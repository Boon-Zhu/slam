"""Explicit robot-local CLI. No retry and no automatic cancellation on exit."""

from __future__ import annotations

import json
import sys
import time
import uuid
from collections.abc import Callable

import rclpy  # type: ignore[import-untyped]
from rclpy.node import Node  # type: ignore[import-untyped]

from dogzilla_capture_interfaces.msg import CaptureEvent, CaptureStatus  # type: ignore[import-untyped]
from dogzilla_capture_interfaces.srv import Stop, SubmitMotion  # type: ignore[import-untyped]

from .cli_arguments import Arguments, parse_arguments
from .node import snapshot_qos, stream_qos


def wait_until(node: Node, condition: Callable[[], bool], deadline: float) -> bool:
    while rclpy.ok() and not condition():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        rclpy.spin_once(node, timeout_sec=min(0.05, remaining))
    return condition()


def run_command(node: Node, arguments: Arguments) -> int:
    statuses: list[CaptureStatus] = []
    events: list[CaptureEvent] = []
    node.create_subscription(
        CaptureStatus, arguments.namespace + "/status", statuses.append, snapshot_qos()
    )
    node.create_subscription(
        CaptureEvent, arguments.namespace + "/events", events.append, stream_qos()
    )
    if not wait_until(
        node, lambda: bool(statuses), time.monotonic() + arguments.timeout_s
    ):
        print("未收到入口状态；未发送请求。", file=sys.stderr)
        return 2
    state = statuses[-1]
    if arguments.command == "status":
        print(
            json.dumps(
                {
                    "session_id": state.session_id,
                    "state": state.state,
                    "enable_motion": state.enable_motion,
                    "current_request_id": state.current_request_id,
                    "feedback_count": state.feedback_count,
                    "invalid_feedback_count": state.invalid_feedback_count,
                    "feedback_paused": state.feedback_paused,
                    "last_error": state.last_error,
                },
                ensure_ascii=False,
            )
        )
        return 0
    request_id = str(uuid.uuid4())
    if arguments.command == "stop":
        service_type = Stop
        endpoint = "/stop"
        request = Stop.Request(session_id=state.session_id, request_id=request_id)
        expected_event = "STOP_REQUEST_COMPLETED"
    else:
        service_type = SubmitMotion
        endpoint = "/submit_motion"
        request = SubmitMotion.Request(
            session_id=state.session_id,
            request_id=request_id,
            action=arguments.command,
            magnitude=arguments.magnitude,
            duration_s=arguments.duration_s,
        )
        expected_event = "MOTION_WRITTEN"
    client = node.create_client(service_type, arguments.namespace + endpoint)
    if not client.wait_for_service(timeout_sec=arguments.timeout_s):
        print("入口服务不可用；未发送请求。", file=sys.stderr)
        return 2
    try:
        future = client.call_async(request)
        deadline = time.monotonic() + arguments.timeout_s
        if not wait_until(node, future.done, deadline):
            print(
                f"请求 {request_id} 响应未知；不会自动重试，请检查 status/events。",
                file=sys.stderr,
            )
            return 3
        response = future.result()
    except Exception as exc:  # noqa: BLE001 - external ROS errors leave execution unknown.
        # Even call_async can fail after handing the request to middleware.
        # A transport exception cannot establish that no command was sent.
        print(
            f"请求 {request_id} 执行结果未知（{type(exc).__name__}: {exc}）；"
            "请求可能已经发送，不会自动重试或取消，请检查 status/events。",
            file=sys.stderr,
        )
        return 3
    if response is None:
        print(f"请求 {request_id} 无响应结果；不会自动重试。", file=sys.stderr)
        return 3
    print(
        json.dumps(
            {
                "request_id": request_id,
                "accepted": response.accepted,
                "reason": response.reason,
            },
            ensure_ascii=False,
        )
    )
    if not response.accepted:
        return 2

    def completed() -> bool:
        return any(
            event.request_id == request_id
            and (
                event.kind == expected_event
                or event.kind.endswith(("_FAILED", "_CANCELLED"))
            )
            for event in events
        )

    try:
        execution_observed = wait_until(
            node, completed, time.monotonic() + arguments.timeout_s
        )
    except Exception as exc:  # noqa: BLE001 - external ROS errors leave execution unknown.
        print(
            f"请求 {request_id} 已受理，串口执行结果未知"
            f"（{type(exc).__name__}: {exc}）；不会重发或自动取消。",
            file=sys.stderr,
        )
        return 3
    if not execution_observed:
        print(
            f"请求 {request_id} 已受理，串口执行结果未知；不会重发或自动取消。",
            file=sys.stderr,
        )
        return 3
    event = next(
        event
        for event in events
        if event.request_id == request_id
        and (
            event.kind == expected_event
            or event.kind.endswith(("_FAILED", "_CANCELLED"))
        )
    )
    print(
        json.dumps(
            {
                "request_id": event.request_id,
                "event": event.kind,
                "wall_ns": event.wall_ns,
                "mono_ns": event.mono_ns,
                "detail": event.detail,
                "physical_state": "not_verified",
            },
            ensure_ascii=False,
        )
    )
    return 0 if event.kind == expected_event else 2


def main(args: list[str] | None = None) -> None:
    arguments = parse_arguments(args)
    rclpy.init(args=[])
    node = rclpy.create_node("capture_operator_" + uuid.uuid4().hex[:8])
    result = 3
    try:
        result = run_command(node, arguments)
    except KeyboardInterrupt:
        print("CLI 已退出；不自动取消或重发动作，请检查机器人端状态。", file=sys.stderr)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(result)


if __name__ == "__main__":
    main()
