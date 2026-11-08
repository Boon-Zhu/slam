"""Real Humble transport tests with an explicitly synthetic device backend."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator

import pytest
import rclpy
from dogzilla_device_capture.node import CaptureNode, snapshot_qos, stream_qos
from rclpy.context import Context
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter

from dogzilla_capture_interfaces.msg import (
    CaptureEvent,
    CaptureMetadata,
    CaptureStatus,
    Feedback,
)
from dogzilla_capture_interfaces.srv import Stop, SubmitMotion


def spin_until(
    executor: MultiThreadedExecutor, condition: Callable[[], bool], timeout: float = 5.0
) -> None:
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.02)
    assert condition(), "ROS condition did not become true before deadline"


@pytest.fixture
def ros_entry() -> Iterator[
    tuple[Context, MultiThreadedExecutor, CaptureNode, object, str]
]:
    context = Context()
    rclpy.init(context=context)
    namespace = "/capture_test_" + uuid.uuid4().hex[:8]
    entry = CaptureNode(
        context=context,
        namespace=namespace,
        parameter_overrides=[
            Parameter("backend", value="mock"),
            Parameter("enable_motion", value=True),
        ],
    )
    observer = rclpy.create_node("observer_" + uuid.uuid4().hex[:8], context=context)
    executor = MultiThreadedExecutor(num_threads=4, context=context)
    executor.add_node(entry)
    executor.add_node(observer)
    spin_until(executor, lambda: entry.controller.status().state == "READY")
    try:
        yield context, executor, entry, observer, namespace
    finally:
        entry.close()
        executor.shutdown(timeout_sec=3.0)
        observer.destroy_node()
        entry.destroy_node()
        rclpy.shutdown(context=context)


def test_services_feedback_and_late_metadata(ros_entry: tuple) -> None:
    _, executor, entry, observer, namespace = ros_entry
    samples, events, metadata, statuses = [], [], [], []
    observer.create_subscription(
        Feedback, namespace + "/feedback", samples.append, stream_qos()
    )
    observer.create_subscription(
        CaptureEvent, namespace + "/events", events.append, stream_qos()
    )
    spin_until(executor, lambda: entry.controller.metadata().firmware is not None)
    observer.create_subscription(
        CaptureMetadata, namespace + "/metadata", metadata.append, snapshot_qos()
    )
    observer.create_subscription(
        CaptureStatus, namespace + "/status", statuses.append, snapshot_qos()
    )
    spin_until(
        executor, lambda: len(samples) >= 4 and bool(metadata) and bool(statuses)
    )
    assert metadata[-1].has_firmware
    assert metadata[-1].firmware.text == "MOCK-ONLY"
    assert dict(zip(metadata[-1].keys, metadata[-1].values))["backend"] == "mock"
    assert all(
        sample.session_id == entry.controller.status().session_id for sample in samples
    )
    assert any(sample.valid and sample.chunks for sample in samples)
    submit = observer.create_client(SubmitMotion, namespace + "/submit_motion")
    assert submit.wait_for_service(timeout_sec=3)
    request = SubmitMotion.Request(
        session_id=statuses[-1].session_id,
        request_id="one-action",
        action="forward",
        magnitude=5,
        duration_s=0.15,
    )
    response = submit.call_async(request)
    spin_until(executor, response.done)
    assert response.result().accepted
    spin_until(
        executor,
        lambda: any(
            event.kind == "STOP_WRITTEN" and event.request_id == "one-action"
            for event in events
        ),
    )
    written = [event for event in events if event.request_id == "one-action"]
    assert any(event.kind == "MOTION_WRITTEN" for event in written)
    assert next(
        event.mono_ns for event in written if event.kind == "STOP_WRITTEN"
    ) >= next(event.mono_ns for event in written if event.kind == "MOTION_WRITTEN")
    duplicate = submit.call_async(request)
    spin_until(executor, duplicate.done)
    spin_until(executor, lambda: entry.controller.status().state == "READY")
    assert (
        len(
            [
                event
                for event in events
                if event.kind == "MOTION_WRITTEN" and event.request_id == "one-action"
            ]
        )
        == 1
    )
    result = entry.set_parameters([Parameter("use_sim_time", value=True)])
    assert not result[0].successful


def test_stop_service_survives_blocked_publication(ros_entry: tuple) -> None:
    import threading

    _, executor, entry, observer, namespace = ros_entry
    blocked, release = threading.Event(), threading.Event()
    real_publisher = entry._feedback_pub

    class BlockingPublisher:
        def publish(self, _message: object) -> None:
            blocked.set()
            release.wait(timeout=5)

    entry._feedback_pub = BlockingPublisher()
    try:
        spin_until(executor, blocked.is_set)
        stop = observer.create_client(Stop, namespace + "/stop")
        assert stop.wait_for_service(timeout_sec=2)
        future = stop.call_async(
            Stop.Request(
                session_id=entry.controller.status().session_id,
                request_id="stop-while-publish-blocked",
            )
        )
        spin_until(executor, future.done, timeout=1)
        assert future.result().accepted
        assert not release.is_set()
        completed_events = []

        def stop_written() -> bool:
            completed_events.extend(entry.controller.drain_events())
            return any(
                event.kind == "STOP_REQUEST_COMPLETED"
                and event.request_id == "stop-while-publish-blocked"
                for event in completed_events
            )

        spin_until(executor, stop_written, timeout=1)
    finally:
        release.set()
        entry._feedback_pub = real_publisher


def test_default_readonly_and_sim_time_rejection() -> None:
    context = Context()
    rclpy.init(context=context)
    node = CaptureNode(
        context=context,
        namespace="/readonly_" + uuid.uuid4().hex[:8],
        parameter_overrides=[Parameter("backend", value="mock")],
    )
    executor = MultiThreadedExecutor(context=context)
    executor.add_node(node)
    try:
        spin_until(executor, lambda: node.controller.status().state == "READY")
        assert node.controller.status().enable_motion is False
        assert not node.controller.request_stop(
            node.controller.status().session_id, "readonly-stop"
        ).accepted
    finally:
        node.close()
        executor.shutdown(timeout_sec=3)
        node.destroy_node()
        rclpy.shutdown(context=context)


def test_shutdown_stop_failure_retains_raw_evidence(monkeypatch, capsys) -> None:
    from dogzilla_device_capture.contracts import DeviceError, SerialChunk
    from dogzilla_device_capture.mock_device import MockDevice

    from dogzilla_device_capture import node as node_module

    class StopFailureDevice(MockDevice):
        def stop(self):
            self._check_owner()
            raise DeviceError(
                "fixture-stop-write-failure",
                (SerialChunk("partial_write", time.monotonic_ns(), b"\x55\x00"),),
            )

    monkeypatch.setattr(node_module, "MockDevice", StopFailureDevice)
    context = Context()
    rclpy.init(context=context)
    entry = CaptureNode(
        context=context,
        namespace="/close_test_" + uuid.uuid4().hex[:8],
        parameter_overrides=[
            Parameter("backend", value="mock"),
            Parameter("enable_motion", value=True),
        ],
    )
    executor = MultiThreadedExecutor(context=context)
    executor.add_node(entry)
    try:
        spin_until(executor, lambda: entry.controller.status().state == "READY")
        assert entry.close() is False
        assert entry.close() is False
        text = capsys.readouterr().err
        assert "shutdown_audit" in text
        assert "STOP_FAILED" in text
        assert "fixture-stop-write-failure" in text
        assert "5500" in text
        assert '"success": false' in text
    finally:
        executor.shutdown(timeout_sec=3)
        entry.destroy_node()
        rclpy.shutdown(context=context)


def test_installed_cli_status_motion_and_stop(ros_entry: tuple, tmp_path) -> None:
    import json
    import subprocess

    _, executor, entry, _observer, namespace = ros_entry

    def invoke(command: list[str]) -> list[dict]:
        output_path = tmp_path / ("-".join(command[:1]) + ".log")
        with output_path.open("w") as output:
            process = subprocess.Popen(
                [
                    "ros2",
                    "run",
                    "dogzilla_device_capture",
                    "capturectl",
                    "--namespace",
                    namespace,
                    *command,
                ],
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            try:
                spin_until(executor, lambda: process.poll() is not None, timeout=12)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
        text = output_path.read_text()
        assert process.returncode == 0, text
        return [json.loads(line) for line in text.splitlines() if line.startswith("{")]

    status = invoke(["status"])
    assert status[-1]["state"] == "READY"
    result = invoke(["forward", "--input", "5", "--duration", "3"])
    assert result[0]["accepted"]
    assert result[-1]["event"] == "MOTION_WRITTEN"
    assert result[-1]["physical_state"] == "not_verified"
    # CLI process has exited, while the robot-side action remains active.
    assert entry.controller.status().state == "RUNNING"
    result = invoke(["stop"])
    assert result[0]["accepted"]
    assert result[-1]["event"] == "STOP_REQUEST_COMPLETED"
    spin_until(executor, lambda: entry.controller.status().state == "READY")


@pytest.mark.parametrize("stop_fails", [False, True])
def test_node_process_sigterm_writes_shutdown_audit(tmp_path, stop_fails: bool) -> None:
    import json
    import signal
    import subprocess
    import sys
    from pathlib import Path

    from ament_index_python.packages import get_package_prefix

    namespace = "/signal_test_" + uuid.uuid4().hex[:8]
    ros_arguments = [
        "--ros-args",
        "-p",
        "backend:=mock",
        "-p",
        "enable_motion:=true",
        "-r",
        "__ns:=" + namespace,
    ]
    executable = (
        Path(get_package_prefix("dogzilla_device_capture"))
        / "lib/dogzilla_device_capture/capture_node"
    )
    if stop_fails:
        injected = (
            "from dogzilla_device_capture import node\n"
            "from dogzilla_device_capture.contracts import DeviceError\n"
            "def fail(self):\n"
            '    raise DeviceError("injected-exit-stop-error")\n'
            "node.MockDevice.stop = fail\n"
            "node.main()\n"
        )
        command = [sys.executable, "-c", injected, *ros_arguments]
    else:
        command = [str(executable), *ros_arguments]
    context = Context()
    rclpy.init(context=context)
    observer = rclpy.create_node(
        "signal_observer_" + uuid.uuid4().hex[:8], context=context
    )
    executor = MultiThreadedExecutor(context=context)
    executor.add_node(observer)
    statuses = []
    observer.create_subscription(
        CaptureStatus, namespace + "/status", statuses.append, snapshot_qos()
    )
    log_path = tmp_path / "node.log"
    process = None
    try:
        with log_path.open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            spin_until(
                executor,
                lambda: any(item.state == "READY" for item in statuses),
                timeout=10,
            )
            process.send_signal(signal.SIGTERM)
            spin_until(executor, lambda: process.poll() is not None, timeout=8)
        text = log_path.read_text()
        audits = [
            json.loads(line)
            for line in text.splitlines()
            if line.startswith('{"kind": "shutdown_audit"')
        ]
        assert len(audits) == 1, text
        assert audits[0]["worker_exited"] is True
        assert audits[0]["success"] is (not stop_fails)
        assert audits[0]["status"]["state"] == "CLOSED"
        event_kinds = {event["kind"] for event in audits[0]["unpublished_events"]}
        assert ("STOP_FAILED" if stop_fails else "STOP_WRITTEN") in event_kinds
        assert (process.returncode == 0) is (not stop_fails), text
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=3)
        executor.shutdown(timeout_sec=3)
        observer.destroy_node()
        rclpy.shutdown(context=context)
