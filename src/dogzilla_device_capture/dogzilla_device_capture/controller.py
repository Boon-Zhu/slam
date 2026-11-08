"""Single-owner hardware scheduling, independent of ROS and vendor imports."""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from .contracts import (
    Clock,
    Decision,
    Device,
    DeviceError,
    Event,
    Feedback,
    Metadata,
    MotionRequest,
    SerialChunk,
    Status,
)

DEFAULT_RATES: tuple[tuple[str, float], ...] = (
    ("read_imu_raw", 20.0),
    ("read_motor", 10.0),
    ("read_battery", 1.0),
    ("read_roll", 1.0),
    ("read_pitch", 1.0),
    ("read_yaw", 1.0),
)


@dataclass(frozen=True)
class ControllerConfig:
    enable_motion: bool = False
    feedback_capacity: int = 1024
    rates: tuple[tuple[str, float], ...] = DEFAULT_RATES
    poll_interval_s: float = 0.001
    clock_jump_threshold_ns: int = 100_000_000

    def __post_init__(self) -> None:
        if self.feedback_capacity < 1:
            raise ValueError("feedback_capacity must be positive")
        if not math.isfinite(self.poll_interval_s) or self.poll_interval_s <= 0:
            raise ValueError("poll_interval_s must be finite and positive")
        if self.clock_jump_threshold_ns < 1:
            raise ValueError("clock_jump_threshold_ns must be positive")
        allowed = {method for method, _ in DEFAULT_RATES}
        names = [method for method, _ in self.rates]
        if len(names) != len(set(names)) or set(names) != allowed:
            raise ValueError("rates must contain each dynamic feedback method once")
        for _, rate in self.rates:
            if not math.isfinite(rate) or not 0 < rate <= 1_000:
                raise ValueError("feedback rates must be finite and in (0, 1000]")


class SystemClock:
    def monotonic_ns(self) -> int:
        return time.monotonic_ns()

    def time_ns(self) -> int:
        return time.time_ns()


class CaptureController:
    """Callbacks submit work; only the worker invokes the device factory/API.

    ``step`` is a deterministic alternative to ``start`` for unit tests. These
    execution modes must not be mixed. Public status/drain methods never touch
    the device, and no publisher or file writer runs on the hardware thread.
    """

    def __init__(
        self,
        device_factory: Callable[[], Device],
        config: ControllerConfig | None = None,
        clock: Clock | None = None,
        session_id: str | None = None,
    ) -> None:
        self.config = config or ControllerConfig()
        self.session_id = session_id or str(uuid.uuid4())
        self._clock = clock or SystemClock()
        self._factory = device_factory
        self._condition = threading.Condition(threading.RLock())
        self._thread: threading.Thread | None = None
        self._owner_id: int | None = None
        self._device: Device | None = None
        self._initialized = False
        self._closing = False
        self._closed = False
        self._faulted = False
        self._state = "STARTING"
        self._last_error = ""
        self._pending: MotionRequest | None = None
        self._current: MotionRequest | None = None
        self._deadline_ns: int | None = None
        self._stops: deque[str] = deque()
        self._requests: dict[str, MotionRequest | str] = {}
        self._decisions: dict[str, Decision] = {}
        self._feedback: deque[Feedback] = deque()
        self._events: deque[Event] = deque()
        self._feedback_count = 0
        self._invalid_count = 0
        self._paused = False
        self._paused_at_ns = 0
        self._backpressure_count = 0
        self._periods = {
            method: max(1, round(1_000_000_000 / rate))
            for method, rate in self.config.rates
        }
        self._due: dict[str, int] = {}
        self._firmware_pending = True
        self._firmware: Feedback | None = None
        self._device_metadata: dict[str, str] = {}
        self._last_clock_pair: tuple[int, int] | None = None

    def start(self) -> None:
        with self._condition:
            if self._thread is not None or self._owner_id is not None or self._closed:
                raise RuntimeError("controller execution has already started")
            self._thread = threading.Thread(
                target=self._run, name="capture-device-owner", daemon=False
            )
            self._thread.start()

    def submit_motion(self, request: MotionRequest) -> Decision:
        with self._condition:
            reason = self._request_identity_error(
                request.session_id, request.request_id
            )
            if reason:
                return self._reject(request.request_id, reason)
            previous = self._duplicate(request.request_id, request)
            if previous is not None:
                return previous
            reason = self._motion_error(request)
            if not reason and (self._pending is not None or self._current is not None):
                reason = "busy"
            if not reason and self._stops:
                reason = "stop_pending"
            decision = Decision(not reason, reason or "accepted", request.request_id)
            self._remember(request.request_id, request, decision)
            if reason:
                self._emit("REQUEST_REJECTED", request.request_id, reason)
            else:
                self._pending = request
                self._emit(
                    "REQUEST_ACCEPTED",
                    request.request_id,
                    json.dumps(
                        {
                            "action": request.action,
                            "magnitude": request.magnitude,
                            "duration_s": request.duration_s,
                        },
                        allow_nan=False,
                    ),
                )
                self._condition.notify_all()
            return decision

    def request_stop(self, session_id: str, request_id: str) -> Decision:
        with self._condition:
            reason = self._request_identity_error(session_id, request_id)
            if reason:
                return self._reject(request_id, reason)
            previous = self._duplicate(request_id, "stop")
            if previous is not None:
                return previous
            if not self.config.enable_motion:
                reason = "motion_disabled"
            elif self._closing or self._closed:
                reason = "closing"
            elif not self._initialized or self._device is None:
                reason = "not_ready"
            decision = Decision(not reason, reason or "accepted", request_id)
            self._remember(request_id, "stop", decision)
            if reason:
                self._emit("REQUEST_REJECTED", request_id, reason)
            else:
                self._stops.append(request_id)
                self._emit("STOP_REQUESTED", request_id, "manual")
                self._condition.notify_all()
            return decision

    def status(self) -> Status:
        with self._condition:
            request = self._current or self._pending
            return Status(
                session_id=self.session_id,
                state=self._state,
                current_request_id=request.request_id if request else "",
                enable_motion=self.config.enable_motion,
                feedback_count=self._feedback_count,
                invalid_feedback_count=self._invalid_count,
                feedback_paused=self._paused,
                backpressure_count=self._backpressure_count,
                last_error=self._last_error,
                wall_ns=self._clock.time_ns(),
                mono_ns=self._clock.monotonic_ns(),
            )

    def metadata(self) -> Metadata:
        with self._condition:
            entries = dict(self._device_metadata)
            entries.update(
                {
                    "enable_motion": str(self.config.enable_motion).lower(),
                    "feedback_capacity": str(self.config.feedback_capacity),
                    "feedback_target_rates_hz": json.dumps(dict(self.config.rates)),
                    "time_semantics": "host request/receipt; not device sample time",
                    "vendor_units": "unverified; retain vendor order and raw bytes",
                    "clock_jump_threshold_ns": str(self.config.clock_jump_threshold_ns),
                }
            )
            return Metadata(
                self.session_id,
                self._clock.time_ns(),
                self._clock.monotonic_ns(),
                entries,
                self._firmware,
            )

    @property
    def has_fault(self) -> bool:
        """Distinguish fatal control/close failures from invalid feedback samples."""
        with self._condition:
            return self._faulted

    def drain_feedback(self, limit: int = 100) -> list[Feedback]:
        with self._condition:
            result = [
                self._feedback.popleft()
                for _ in range(min(max(limit, 0), len(self._feedback)))
            ]
            self._condition.notify_all()
            return result

    def drain_events(self, limit: int = 100) -> list[Event]:
        with self._condition:
            return [
                self._events.popleft()
                for _ in range(min(max(limit, 0), len(self._events)))
            ]

    def close(self, timeout_s: float = 3.0) -> bool:
        if not math.isfinite(timeout_s) or timeout_s < 0:
            raise ValueError("timeout_s must be finite and nonnegative")
        with self._condition:
            self._closing = True
            self._condition.notify_all()
            thread = self._thread
        if thread is None:
            if self._owner_id is not None and self._owner_id != threading.get_ident():
                raise RuntimeError("manual controller must close on its owner thread")
            self.step()
            return self._closed
        if thread is threading.current_thread():
            return False
        thread.join(timeout_s)
        return not thread.is_alive()

    def step(self) -> None:
        """Perform at most one hardware transaction, on a single owner thread."""
        identity = threading.get_ident()
        if self._thread is not None and self._thread is not threading.current_thread():
            raise RuntimeError("cannot manually step a background controller")
        if self._owner_id is None:
            self._owner_id = identity
        elif self._owner_id != identity:
            raise RuntimeError("device operations must remain on one owner thread")
        with self._condition:
            if self._closed:
                return
            closing = self._closing
        if closing:
            self._finish()
            return
        if not self._initialized:
            self._initialize()
            return
        with self._condition:
            self._observe_clock()
            stop_ids = tuple(self._stops)
            self._stops.clear()
            timed_out = (
                self._deadline_ns is not None
                and self._clock.monotonic_ns() >= self._deadline_ns
            )
            if stop_ids or timed_out:
                if timed_out and self._current is not None:
                    self._emit("MOTION_DEADLINE", self._current.request_id)
                operation = "stop"
                request = None
            elif self._faulted:
                return
            elif self._pending is not None:
                request = self._pending
                self._pending = None
                self._current = request
                self._state = "STARTING_MOTION"
                operation = "move"
            else:
                request = None
                operation = "query"
        if operation == "stop":
            self._perform_stop(stop_ids, "duration_elapsed" if timed_out else "manual")
        elif operation == "move" and request is not None:
            self._perform_motion(request)
        else:
            self._perform_query()

    def _run(self) -> None:
        try:
            while not self._closed:
                self.step()
                with self._condition:
                    if not self._closed:
                        self._condition.wait(self.config.poll_interval_s)
        except Exception as exc:
            self._mark_fault(f"worker_error: {exc}")
            self._finish()

    def _initialize(self) -> None:
        try:
            self._device = self._factory()
            device_metadata = self._device.metadata()
        except Exception as exc:
            with self._condition:
                self._initialized = True
            self._mark_fault(f"initialization_error: {exc}")
            return
        with self._condition:
            self._device_metadata = dict(device_metadata)
            self._due = {name: self._clock.monotonic_ns() for name in self._periods}
            self._initialized = True
            self._state = "READY"
            self._observe_clock()
            self._emit(
                "READY",
                "",
                "motion enabled" if self.config.enable_motion else "read only",
            )

    def _perform_motion(self, request: MotionRequest) -> None:
        device = self._device
        if device is None:
            self._mark_fault("device_unavailable")
            return
        try:
            cleared = device.stop()
            with self._condition:
                self._emit("AXES_CLEARED", request.request_id, chunks=cleared)
                if self._closing or self._stops:
                    self._emit(
                        "MOTION_CANCELLED", request.request_id, "before motion write"
                    )
                    self._current = None
                    self._state = "STOPPING"
                    return
            chunks = device.move(request.action, request.magnitude)
            start_ns = self._clock.monotonic_ns()
            with self._condition:
                self._deadline_ns = start_ns + round(request.duration_s * 1_000_000_000)
                self._state = "RUNNING"
                self._emit(
                    "MOTION_WRITTEN",
                    request.request_id,
                    json.dumps(
                        {
                            "action": request.action,
                            "magnitude": request.magnitude,
                            "duration_s": request.duration_s,
                            "motion_start_mono_ns": start_ns,
                            "deadline_mono_ns": self._deadline_ns,
                        },
                        allow_nan=False,
                    ),
                    chunks,
                )
        except Exception as exc:
            chunks = exc.chunks if isinstance(exc, DeviceError) else ()
            with self._condition:
                self._emit("MOTION_FAILED", request.request_id, str(exc), chunks)
            self._mark_fault(f"motion_error: {exc}")
            self._perform_stop((), "motion_failed")

    def _perform_stop(self, stop_ids: tuple[str, ...], reason: str) -> None:
        with self._condition:
            current = self._current or self._pending
            if self._pending is not None:
                self._emit(
                    "MOTION_CANCELLED",
                    self._pending.request_id,
                    "stopped before motion write",
                )
            self._pending = None
            self._deadline_ns = None
            self._state = "STOPPING"
        request_id = current.request_id if current else ""
        try:
            device = self._device
            if device is None:
                raise DeviceError("device_unavailable")
            chunks = device.stop()
            with self._condition:
                self._emit("STOP_WRITTEN", request_id, reason, chunks)
                for stop_id in stop_ids:
                    self._emit(
                        "STOP_REQUEST_COMPLETED",
                        stop_id,
                        f"stopped_request={request_id}",
                    )
        except Exception as exc:
            chunks = exc.chunks if isinstance(exc, DeviceError) else ()
            with self._condition:
                self._emit("STOP_FAILED", request_id, str(exc), chunks)
                for stop_id in stop_ids:
                    self._emit("STOP_REQUEST_FAILED", stop_id, str(exc))
            self._mark_fault(f"stop_error: {exc}")
        finally:
            with self._condition:
                self._current = None
                self._state = "FAULT" if self._faulted else "READY"

    def _perform_query(self) -> None:
        with self._condition:
            if self._control_pending():
                return
            now_ns = self._clock.monotonic_ns()
            if len(self._feedback) >= self.config.feedback_capacity:
                if not self._paused:
                    self._paused = True
                    self._paused_at_ns = now_ns
                    self._backpressure_count += 1
                    self._emit("FEEDBACK_PAUSED", "", "output buffer full")
                return
            if self._paused:
                self._paused = False
                self._emit(
                    "FEEDBACK_RESUMED", "", f"paused_ns={now_ns - self._paused_at_ns}"
                )
            if self._firmware_pending:
                method = "read_version"
                self._firmware_pending = False
            else:
                method = min(self._due, key=lambda key: self._due[key])
                if self._due[method] > now_ns:
                    return
                skipped = (now_ns - self._due[method]) // self._periods[method]
                if skipped:
                    self._emit("FEEDBACK_SCHEDULE_SKIPPED", "", f"{method}:{skipped}")
                self._due[method] = now_ns + self._periods[method]
            wall_ns = self._clock.time_ns()
        device = self._device
        if device is None:
            return
        try:
            sample = device.query(method, self._control_pending)
        except Exception as exc:
            sample = Feedback(
                method=method,
                sequence=self._feedback_count + 1,
                wall_start_ns=wall_ns,
                wall_end_ns=self._clock.time_ns(),
                mono_start_ns=now_ns,
                mono_end_ns=self._clock.monotonic_ns(),
                chunks=exc.chunks if isinstance(exc, DeviceError) else (),
                error=f"io_error: {exc}",
            )
        with self._condition:
            self._feedback.append(sample)
            self._feedback_count += 1
            if not sample.valid:
                self._invalid_count += 1
                self._last_error = sample.error
            if method == "read_version":
                self._firmware = sample
            elif self._clock.monotonic_ns() >= self._due[method]:
                self._due[method] = self._clock.monotonic_ns() + self._periods[method]
            io_failed = sample.error.startswith(("serial_error", "io_error"))
            moving = self._current is not None
        if io_failed:
            self._mark_fault(sample.error)
            if moving:
                self._perform_stop((), "device_io_failed")

    def _control_pending(self) -> bool:
        with self._condition:
            return bool(
                self._closing
                or self._stops
                or self._pending is not None
                or (
                    self._deadline_ns is not None
                    and self._clock.monotonic_ns() >= self._deadline_ns
                )
            )

    def _finish(self) -> None:
        with self._condition:
            if self._closed:
                return
            pending = self._pending
            self._pending = None
            if pending is not None:
                self._emit(
                    "MOTION_CANCELLED",
                    pending.request_id,
                    "shutdown before motion write",
                )
            stop_ids = tuple(self._stops)
            self._stops.clear()
        if self._device is not None:
            if self.config.enable_motion:
                self._perform_stop(stop_ids, "shutdown")
            try:
                self._device.close()
            except Exception as exc:
                self._mark_fault(f"close_error: {exc}")
        with self._condition:
            self._closed = True
            self._state = "CLOSED"
            self._emit("CLOSED", "", self._last_error if self._faulted else "")
            self._condition.notify_all()

    def _motion_error(self, request: MotionRequest) -> str:
        if not self.config.enable_motion:
            return "motion_disabled"
        if self._closing or self._closed:
            return "closing"
        if not self._initialized or self._device is None:
            return "not_ready"
        if self._faulted:
            return "fault_requires_restart"
        if request.action not in ("forward", "left", "right"):
            return "invalid_action"
        if isinstance(request.magnitude, bool) or not isinstance(
            request.magnitude, int
        ):
            return "invalid_magnitude"
        low, high = (1, 20) if request.action == "forward" else (30, 70)
        if not low <= request.magnitude <= high:
            return "invalid_magnitude"
        if (
            isinstance(request.duration_s, bool)
            or not math.isfinite(request.duration_s)
            or request.duration_s <= 0
            or not math.isfinite(request.duration_s * 1_000_000_000)
        ):
            return "invalid_duration"
        return ""

    def _request_identity_error(self, session_id: str, request_id: str) -> str:
        if session_id != self.session_id:
            return "stale_session"
        if not request_id or len(request_id) > 128:
            return "invalid_request_id"
        return ""

    def _duplicate(
        self, request_id: str, value: MotionRequest | str
    ) -> Decision | None:
        if request_id not in self._requests:
            return None
        if self._requests[request_id] != value:
            return self._reject(request_id, "request_id_conflict")
        previous = self._decisions[request_id]
        self._emit("REQUEST_DUPLICATE", request_id, previous.reason)
        return Decision(previous.accepted, f"duplicate:{previous.reason}", request_id)

    def _remember(
        self, request_id: str, value: MotionRequest | str, decision: Decision
    ) -> None:
        self._requests[request_id] = value
        self._decisions[request_id] = decision

    def _reject(self, request_id: str, reason: str) -> Decision:
        self._emit("REQUEST_REJECTED", request_id, reason)
        return Decision(False, reason, request_id)

    def _mark_fault(self, message: str) -> None:
        with self._condition:
            self._faulted = True
            self._last_error = message
            self._state = "FAULT"
            self._emit("FAULT", "", message)

    def _emit(
        self,
        kind: str,
        request_id: str,
        detail: str = "",
        chunks: tuple[SerialChunk, ...] = (),
    ) -> None:
        self._events.append(
            Event(
                kind,
                request_id,
                self._clock.time_ns(),
                self._clock.monotonic_ns(),
                detail,
                chunks,
            )
        )

    def _observe_clock(self) -> None:
        wall_ns, mono_ns = self._clock.time_ns(), self._clock.monotonic_ns()
        if self._last_clock_pair is not None:
            old_wall, old_mono = self._last_clock_pair
            difference = (wall_ns - old_wall) - (mono_ns - old_mono)
            if abs(difference) >= self.config.clock_jump_threshold_ns:
                self._emit(
                    "CLOCK_JUMP", "", f"wall_minus_monotonic_delta_ns={difference}"
                )
        self._last_clock_pair = (wall_ns, mono_ns)
