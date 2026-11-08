"""ROS boundary for the single-owner capture controller."""

from __future__ import annotations

import json
import math
import signal
import sys
import threading
from collections.abc import Callable
from dataclasses import asdict

import rclpy  # type: ignore[import-untyped]
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult  # type: ignore[import-untyped]
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup  # type: ignore[import-untyped]
from rclpy.context import Context  # type: ignore[import-untyped]
from rclpy.executors import MultiThreadedExecutor  # type: ignore[import-untyped]
from rclpy.node import Node  # type: ignore[import-untyped]
from rclpy.parameter import Parameter  # type: ignore[import-untyped]
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # type: ignore[import-untyped]
from rclpy.signals import SignalHandlerOptions  # type: ignore[import-untyped]

from dogzilla_capture_interfaces.msg import (  # type: ignore[import-untyped]
    CaptureEvent,
    CaptureMetadata,
    CaptureStatus,
)
from dogzilla_capture_interfaces.msg import (
    Feedback as FeedbackMessage,
)
from dogzilla_capture_interfaces.srv import Stop, SubmitMotion  # type: ignore[import-untyped]

from .contracts import Device, Event, Feedback, MotionRequest
from .controller import CaptureController, ControllerConfig
from .mock_device import MockDevice
from .ros_messages import (
    event_message,
    feedback_message,
    metadata_message,
    status_message,
)


def stream_qos() -> QoSProfile:
    return QoSProfile(
        depth=1024,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
    )


def snapshot_qos() -> QoSProfile:
    return QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )


class CaptureNode(Node):  # type: ignore[misc]  # rclpy provides no typed Node base
    def __init__(
        self,
        *,
        context: Context | None = None,
        namespace: str = "/capture/device",
        parameter_overrides: list[Parameter] | None = None,
    ) -> None:
        super().__init__(
            "capture_entry",
            context=context,
            namespace=namespace,
            parameter_overrides=parameter_overrides,
        )
        if self.get_parameter("use_sim_time").value:
            raise ValueError("capture entry requires use_sim_time=false")
        self.add_on_set_parameters_callback(self._validate_parameter_changes)
        backend = self._string_parameter("backend", "vendor")
        enable_motion = self._bool_parameter("enable_motion", False)
        port = self._string_parameter("port", "/dev/ttyAMA0")
        lock_path = self._string_parameter(
            "lock_path", "/run/lock/dogzilla-ttyAMA0.lock"
        )
        fresh_hardware_session = self._bool_parameter("fresh_hardware_session", False)
        capacity = self._int_parameter("feedback_capacity", 1024)
        rates = tuple(
            (method, self._float_parameter(method + "_hz", default))
            for method, default in (
                ("read_imu_raw", 20.0),
                ("read_motor", 10.0),
                ("read_battery", 1.0),
                ("read_roll", 1.0),
                ("read_pitch", 1.0),
                ("read_yaw", 1.0),
            )
        )
        factory: Callable[[], Device]
        if backend == "mock":
            factory = MockDevice
        elif backend == "vendor":

            def factory() -> Device:
                from .vendor_adapter import open_vendor_device

                return open_vendor_device(
                    port=port,
                    lock_path=lock_path,
                    fresh_hardware_session=fresh_hardware_session,
                )
        else:
            raise ValueError("backend must be vendor or mock")
        self.controller = CaptureController(
            factory,
            ControllerConfig(
                enable_motion=enable_motion,
                feedback_capacity=capacity,
                rates=rates,
            ),
        )
        self._feedback_pub = self.create_publisher(
            FeedbackMessage, "feedback", stream_qos()
        )
        self._events_pub = self.create_publisher(CaptureEvent, "events", stream_qos())
        self._status_pub = self.create_publisher(
            CaptureStatus, "status", snapshot_qos()
        )
        self._metadata_pub = self.create_publisher(
            CaptureMetadata, "metadata", snapshot_qos()
        )
        self._control_group = MutuallyExclusiveCallbackGroup()
        self._publication_group = MutuallyExclusiveCallbackGroup()
        self.create_service(
            SubmitMotion,
            "submit_motion",
            self._submit_motion,
            callback_group=self._control_group,
        )
        self.create_service(
            Stop, "stop", self._stop, callback_group=self._control_group
        )
        self._metadata_signature: tuple[object, ...] | None = None
        self._publication_timer = self.create_timer(
            0.01, self.publish_pending, callback_group=self._publication_group
        )
        self._status_timer = self.create_timer(
            0.1, self.publish_status, callback_group=self._publication_group
        )
        self._closed = False
        self._closing = False
        self._close_success = False
        self._publication_lock = threading.Lock()
        self._publication_batch: list[Event | Feedback] = []
        self.controller.start()

    def _parameter(self, name: str, default: str | bool | int | float) -> object:
        return self.declare_parameter(
            name, default, ParameterDescriptor(read_only=True)
        ).value

    def _string_parameter(self, name: str, default: str) -> str:
        value = self._parameter(name, default)
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        return value

    def _bool_parameter(self, name: str, default: bool) -> bool:
        value = self._parameter(name, default)
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be bool")
        return value

    def _int_parameter(self, name: str, default: int) -> int:
        value = self._parameter(name, default)
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
        return value

    def _float_parameter(self, name: str, default: float) -> float:
        value = self._parameter(name, default)
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise ValueError(f"{name} must be numeric")
        return float(value)

    def _validate_parameter_changes(
        self, parameters: list[Parameter]
    ) -> SetParametersResult:
        for parameter in parameters:
            if parameter.name == "use_sim_time" and parameter.value is not False:
                return SetParametersResult(
                    successful=False, reason="live entry requires use_sim_time=false"
                )
        return SetParametersResult(successful=True)

    def _submit_motion(
        self, request: SubmitMotion.Request, response: SubmitMotion.Response
    ) -> SubmitMotion.Response:
        decision = self.controller.submit_motion(
            MotionRequest(
                request.session_id,
                request.request_id,
                request.action,
                request.magnitude,
                request.duration_s,
            )
        )
        response.accepted, response.reason, response.request_id = (
            decision.accepted,
            decision.reason,
            decision.request_id,
        )
        return response

    def _stop(self, request: Stop.Request, response: Stop.Response) -> Stop.Response:
        decision = self.controller.request_stop(request.session_id, request.request_id)
        response.accepted, response.reason, response.request_id = (
            decision.accepted,
            decision.reason,
            decision.request_id,
        )
        return response

    def publish_pending(self) -> None:
        if self._closing:
            return
        session_id = self.controller.status().session_id
        with self._publication_lock:
            self._publication_batch.extend(self.controller.drain_events())
            self._publication_batch.extend(self.controller.drain_feedback())
        while not self._closing:
            with self._publication_lock:
                if not self._publication_batch:
                    return
                item = self._publication_batch[0]
            if isinstance(item, Event):
                self._events_pub.publish(event_message(session_id, item))
            else:
                self._feedback_pub.publish(feedback_message(session_id, item))
            with self._publication_lock:
                self._publication_batch.pop(0)

    def publish_status(self) -> None:
        if self._closing:
            return
        self._status_pub.publish(status_message(self.controller.status()))
        metadata = self.controller.metadata()
        signature = (tuple(sorted(metadata.entries.items())), metadata.firmware)
        if signature != self._metadata_signature:
            self._metadata_pub.publish(metadata_message(metadata))
            self._metadata_signature = signature

    def close(self) -> bool:
        if self._closed:
            return self._close_success
        self._closing = True
        self._publication_timer.cancel()
        self._status_timer.cancel()
        stopped = self.controller.close()
        events = self.controller.drain_events(limit=100000)
        feedback = self.controller.drain_feedback(limit=100000)
        with self._publication_lock:
            unconfirmed = list(self._publication_batch)
        self._close_success = stopped and not self.controller.has_fault
        audit = {
            "kind": "shutdown_audit",
            "worker_exited": stopped,
            "success": self._close_success,
            "status": asdict(self.controller.status()),
            "not_confirmed_in_bag": True,
            "unpublished_events": [asdict(event) for event in events],
            "unpublished_feedback_count": len(feedback),
            "unpublished_feedback": [asdict(sample) for sample in feedback],
            "publication_in_flight_or_unpublished": [
                asdict(item) for item in unconfirmed
            ],
        }
        print(
            json.dumps(audit_value(audit), ensure_ascii=False, allow_nan=False),
            file=sys.stderr,
            flush=True,
        )
        self._closed = stopped
        return self._close_success


def audit_value(value: object) -> object:
    """Encode shutdown evidence, retaining byte strings and nonfinite numbers."""
    if isinstance(value, bytes):
        return {"hex": value.hex()}
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": repr(value)}
    if isinstance(value, dict):
        return {str(key): audit_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [audit_value(item) for item in value]
    return value


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    shutdown = threading.Event()
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    for sig in previous:
        signal.signal(sig, lambda _signum, _frame: shutdown.set())
    node: CaptureNode | None = None
    closed = True
    executor = MultiThreadedExecutor(num_threads=3)
    try:
        node = CaptureNode()
        executor.add_node(node)
        while rclpy.ok() and not shutdown.is_set():
            executor.spin_once(timeout_sec=0.1)
    finally:
        if node is not None:
            closed = node.close()
        callbacks_finished = executor.shutdown(timeout_sec=2.0)
        closed = closed and callbacks_finished
        if node is not None and callbacks_finished:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if not closed:
        raise SystemExit(
            "shutdown incomplete or control/serial failure; inspect shutdown_audit"
        )


if __name__ == "__main__":
    main()
