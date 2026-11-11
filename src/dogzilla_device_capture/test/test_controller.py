"""Control ordering tests use a deterministic clock and a single fake device."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from dogzilla_device_capture.contracts import (
    DeviceError,
    Feedback,
    MotionRequest,
    SerialChunk,
)
from dogzilla_device_capture.controller import CaptureController, ControllerConfig


@dataclass
class FakeClock:
    mono: int = 1_000_000_000
    wall: int = 1_700_000_000_000_000_000

    def monotonic_ns(self) -> int:
        return self.mono

    def time_ns(self) -> int:
        return self.wall

    def advance(self, seconds: float) -> None:
        elapsed = round(seconds * 1e9)
        self.mono += elapsed
        self.wall += elapsed


class FakeDevice:
    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.calls: list[str] = []
        self.threads: set[int] = set()
        self.query_hook: Callable[[Callable[[], bool]], bool] | None = None
        self.move_delay = 0.0
        self.move_error = False
        self.stop_error = False
        self.query_error = ""
        self.sequence = 0

    def _record(self, name: str) -> tuple[SerialChunk, ...]:
        self.calls.append(name)
        self.threads.add(threading.get_ident())
        return (SerialChunk("write", self.clock.monotonic_ns(), name.encode()),)

    def metadata(self) -> dict[str, str]:
        self._record("metadata")
        return {"backend": "fake"}

    def move(self, action: str, magnitude: int) -> tuple[SerialChunk, ...]:
        chunks = self._record(f"move:{action}:{magnitude}")
        self.clock.advance(self.move_delay)
        if self.move_error:
            raise DeviceError("partial movement write", chunks)
        return chunks

    def stop(self) -> tuple[SerialChunk, ...]:
        chunks = self._record("stop")
        if self.stop_error:
            raise DeviceError("stop write failed", chunks)
        return chunks

    def query(self, method: str, interrupt: Callable[[], bool]) -> Feedback:
        self._record(method)
        mono, wall = self.clock.monotonic_ns(), self.clock.time_ns()
        interrupted = self.query_hook(interrupt) if self.query_hook else interrupt()
        self.sequence += 1
        return Feedback(
            method=method,
            sequence=self.sequence,
            wall_start_ns=wall,
            wall_end_ns=self.clock.time_ns(),
            mono_start_ns=mono,
            mono_end_ns=self.clock.monotonic_ns(),
            chunks=(SerialChunk("read", mono, b"raw frame including extra bytes"),),
            values=(0.0,) if interrupted else (1.0,),
            text="4.0.1-Y" if method == "read_version" else "",
            valid=not interrupted and not self.query_error,
            error="interrupted" if interrupted else self.query_error,
        )

    def close(self) -> None:
        self._record("close")


def controller_fixture(
    *, enabled: bool = True, capacity: int = 1024
) -> tuple[CaptureController, FakeDevice, FakeClock]:
    clock = FakeClock()
    device = FakeDevice(clock)
    controller = CaptureController(
        lambda: device,
        ControllerConfig(enable_motion=enabled, feedback_capacity=capacity),
        clock,
        "session",
    )
    controller.step()
    return controller, device, clock


def request(
    ident: str = "move-1",
    action: str = "forward",
    magnitude: int = 5,
    seconds: float = 1.0,
) -> MotionRequest:
    return MotionRequest("session", ident, action, magnitude, seconds)


def kinds(controller: CaptureController) -> list[str]:
    return [event.kind for event in controller.drain_events(1000)]


def test_default_read_only_never_sends_motion_or_stop() -> None:
    controller, device, _ = controller_fixture(enabled=False)
    assert not controller.submit_motion(request()).accepted
    assert not controller.request_stop("session", "stop-1").accepted
    controller.step()
    assert controller.close()
    assert device.calls == ["metadata", "read_version", "close"]


def test_factory_and_every_operation_share_worker_thread() -> None:
    clock = FakeClock()
    device = FakeDevice(clock)
    factory_threads: list[int] = []

    def factory() -> FakeDevice:
        factory_threads.append(threading.get_ident())
        return device

    controller = CaptureController(factory, clock=clock)
    controller.start()
    deadline = time.monotonic() + 1.0
    while controller.status().feedback_count == 0 and time.monotonic() < deadline:
        time.sleep(0.001)
    assert controller.status().feedback_count > 0
    assert controller.close()
    assert device.threads == set(factory_threads)
    assert threading.get_ident() not in device.threads


def test_motion_clears_axes_and_timer_starts_after_write() -> None:
    controller, device, clock = controller_fixture()
    device.move_delay = 0.25
    assert controller.submit_motion(request()).accepted
    controller.step()
    assert device.calls == ["metadata", "stop", "move:forward:5"]
    clock.advance(0.9)
    controller.step()
    assert device.calls[-1] == "read_version"
    clock.advance(0.1)
    controller.step()
    assert device.calls[-1] == "stop"
    assert controller.status().state == "READY"
    assert "MOTION_DEADLINE" in kinds(controller)
    controller.close()


def test_wall_clock_jump_does_not_end_motion() -> None:
    controller, device, clock = controller_fixture()
    controller.submit_motion(request())
    controller.step()
    clock.wall += 9_000_000_000
    controller.step()
    assert controller.status().state == "RUNNING"
    clock.wall -= 99_000_000_000
    clock.advance(1.0)
    controller.step()
    assert device.calls[-1] == "stop"
    assert kinds(controller).count("CLOCK_JUMP") == 2
    controller.close()


def test_stop_cancels_pending_motion_without_sending_it() -> None:
    controller, device, _ = controller_fixture()
    controller.submit_motion(request())
    assert controller.request_stop("session", "stop-1").accepted
    controller.step()
    assert device.calls == ["metadata", "stop"]
    events = controller.drain_events(100)
    assert any(
        e.kind == "MOTION_CANCELLED" and e.request_id == "move-1" for e in events
    )
    assert any(
        e.kind == "STOP_REQUEST_COMPLETED" and e.request_id == "stop-1" for e in events
    )
    controller.close()


def test_explicit_stop_interrupts_feedback_and_precedes_next_read() -> None:
    controller, device, _ = controller_fixture()

    def interrupt_query(interrupt: Callable[[], bool]) -> bool:
        assert controller.request_stop("session", "stop-1").accepted
        assert interrupt()
        return True

    device.query_hook = interrupt_query
    controller.step()
    sample = controller.drain_feedback()[0]
    assert sample.error == "interrupted"
    assert sample.values == (0.0,) and not sample.valid
    assert sample.chunks[0].data == b"raw frame including extra bytes"
    controller.step()
    assert device.calls == ["metadata", "read_version", "stop"]
    controller.close()


def test_deadline_interrupts_feedback_using_monotonic_clock() -> None:
    controller, device, clock = controller_fixture()
    controller.submit_motion(request(seconds=0.1))
    controller.step()

    def cross_deadline(interrupt: Callable[[], bool]) -> bool:
        clock.advance(0.11)
        return interrupt()

    device.query_hook = cross_deadline
    controller.step()
    assert controller.drain_feedback()[0].error == "interrupted"
    controller.step()
    assert device.calls[-1] == "stop"
    assert controller.status().state == "READY"
    controller.close()


def test_new_motion_interrupts_query_without_parallel_device_access() -> None:
    controller, device, _ = controller_fixture()

    def accept_motion(interrupt: Callable[[], bool]) -> bool:
        assert controller.submit_motion(request()).accepted
        return interrupt()

    device.query_hook = accept_motion
    controller.step()
    assert controller.drain_feedback()[0].error == "interrupted"
    controller.step()
    assert device.calls[-2:] == ["stop", "move:forward:5"]
    assert len(device.threads) == 1
    controller.close()


def test_busy_duplicate_conflict_and_old_session_never_queue_motion() -> None:
    controller, device, _ = controller_fixture()
    first = request()
    assert controller.submit_motion(first).accepted
    assert controller.submit_motion(first).reason == "duplicate:accepted"
    assert controller.submit_motion(request(seconds=2)).reason == "request_id_conflict"
    assert controller.submit_motion(request("second")).reason == "busy"
    assert (
        controller.submit_motion(MotionRequest("old", "third", "forward", 5, 1)).reason
        == "stale_session"
    )
    controller.step()
    controller.request_stop("session", "stop-1")
    controller.step()
    assert controller.submit_motion(request("second")).reason == "duplicate:busy"
    assert sum(call.startswith("move:") for call in device.calls) == 1
    controller.close()


@pytest.mark.parametrize(
    ("action", "magnitude", "duration"),
    [
        ("forward", 0, 1.0),
        ("forward", 21, 1.0),
        ("left", 29, 1.0),
        ("right", 71, 1.0),
        ("back", 5, 1.0),
        ("forward", 5, float("nan")),
        ("forward", 5, float("inf")),
        ("forward", 5, -1.0),
        ("forward", 5, 0.0),
        ("forward", 5, 1e308),
    ],
)
def test_invalid_inputs_rejected_without_writes(
    action: str, magnitude: int, duration: float
) -> None:
    controller, device, _ = controller_fixture()
    assert not controller.submit_motion(
        request(action=action, magnitude=magnitude, seconds=duration)
    ).accepted
    controller.step()
    assert "stop" not in device.calls
    controller.close()


def test_partial_motion_failure_preserves_bytes_attempts_stop_and_latches_fault() -> (
    None
):
    controller, device, _ = controller_fixture()
    device.move_error = True
    controller.submit_motion(request())
    controller.step()
    assert device.calls[-3:] == ["stop", "move:forward:5", "stop"]
    assert controller.status().state == "FAULT"
    assert not controller.submit_motion(request("next")).accepted
    events = controller.drain_events()
    failed = next(e for e in events if e.kind == "MOTION_FAILED")
    assert failed.chunks[0].data == b"move:forward:5"
    controller.step()
    assert device.calls[-1] == "stop"
    controller.close()


def test_failed_stop_is_never_reported_as_completed() -> None:
    controller, device, _ = controller_fixture()
    device.stop_error = True
    controller.request_stop("session", "stop-1")
    controller.step()
    events = controller.drain_events()
    assert any(e.kind == "STOP_FAILED" and e.chunks for e in events)
    assert any(
        e.kind == "STOP_REQUEST_FAILED" and e.request_id == "stop-1" for e in events
    )
    assert not any(e.kind == "STOP_REQUEST_COMPLETED" for e in events)
    assert controller.status().state == "FAULT"
    controller.close()


def test_full_feedback_buffer_pauses_queries_but_not_control() -> None:
    controller, device, clock = controller_fixture(capacity=1)
    controller.step()
    clock.advance(1)
    controller.step()
    assert controller.status().feedback_paused
    assert device.calls.count("read_version") == 1
    assert controller.submit_motion(request()).accepted
    controller.step()
    clock.advance(1)
    controller.step()
    assert device.calls[-3:] == ["stop", "move:forward:5", "stop"]
    old = controller.drain_feedback()
    assert old[0].method == "read_version"
    controller.step()
    assert not controller.status().feedback_paused
    assert controller.status().backpressure_count == 1
    assert "FEEDBACK_RESUMED" in kinds(controller)
    controller.close()


def test_no_catch_up_burst_after_slow_query() -> None:
    controller, device, clock = controller_fixture()
    controller.step()  # Version.

    def slow_query(interrupt: Callable[[], bool]) -> bool:
        clock.advance(1)
        return interrupt()

    device.query_hook = slow_query
    controller.step()  # IMU takes one second.
    device.query_hook = None
    for _ in range(7):
        controller.step()
    assert device.calls.count("read_imu_raw") == 1
    assert "FEEDBACK_SCHEDULE_SKIPPED" in kinds(controller)
    controller.close()


def test_timeout_is_invalid_feedback_not_automatic_motion_stop() -> None:
    controller, device, _ = controller_fixture()
    controller.submit_motion(request(seconds=10))
    controller.step()
    device.query_error = "timeout"
    controller.step()
    assert controller.status().state == "RUNNING"
    assert controller.drain_feedback()[0].error == "timeout"
    assert device.calls.count("stop") == 1  # Only pre-motion axis clear.
    controller.close()


def test_serial_failure_does_not_auto_reconnect_or_continue_motion() -> None:
    controller, device, _ = controller_fixture()
    controller.submit_motion(request())
    controller.step()
    device.query_error = "serial_error: unplugged"
    controller.step()
    assert device.calls[-1] == "stop"
    assert controller.status().state == "FAULT"
    before = list(device.calls)
    controller.step()
    assert device.calls == before
    controller.close()


def test_firmware_raw_response_remains_in_metadata_after_queue_drain() -> None:
    controller, _, _ = controller_fixture()
    controller.step()
    first = controller.drain_feedback()[0]
    assert controller.metadata().firmware == first
    assert controller.metadata().entries["backend"] == "fake"
    controller.close()


def test_shutdown_cancels_unstarted_motion_and_does_not_replay_on_restart() -> None:
    controller, device, clock = controller_fixture()
    controller.submit_motion(request())
    assert controller.close()
    assert device.calls == ["metadata", "stop", "close"]
    successor = CaptureController(
        lambda: FakeDevice(clock), ControllerConfig(enable_motion=True), clock
    )
    successor.step()
    assert successor.submit_motion(request()).reason == "stale_session"
    assert successor.status().current_request_id == ""
    successor.close()


def test_startup_failure_is_visible_and_not_retried() -> None:
    calls = 0

    def fail_factory() -> FakeDevice:
        nonlocal calls
        calls += 1
        raise DeviceError("UART held by another process")

    controller = CaptureController(fail_factory)
    controller.step()
    controller.step()
    assert calls == 1
    assert controller.status().state == "FAULT"
    assert "UART held" in controller.status().last_error
    assert controller.close()


def test_multiple_stop_requests_are_acknowledged_after_one_stop_transaction() -> None:
    controller, device, _ = controller_fixture()
    assert controller.request_stop("session", "s1").accepted
    assert controller.request_stop("session", "s2").accepted
    controller.step()
    assert device.calls.count("stop") == 1
    completed = [
        e.request_id
        for e in controller.drain_events()
        if e.kind == "STOP_REQUEST_COMPLETED"
    ]
    assert completed == ["s1", "s2"]
    controller.close()


def test_events_preserve_requested_duration_and_written_deadline() -> None:
    controller, device, clock = controller_fixture()
    device.move_delay = 0.25
    assert controller.submit_motion(request(seconds=0.75)).accepted
    controller.step()
    events = controller.drain_events()
    accepted = json.loads(
        next(e.detail for e in events if e.kind == "REQUEST_ACCEPTED")
    )
    written = json.loads(next(e.detail for e in events if e.kind == "MOTION_WRITTEN"))
    assert accepted == {"action": "forward", "magnitude": 5, "duration_s": 0.75}
    assert written["motion_start_mono_ns"] == clock.monotonic_ns()
    assert written["deadline_mono_ns"] - written["motion_start_mono_ns"] == 750_000_000
    assert written["duration_s"] == accepted["duration_s"]
    controller.close()
