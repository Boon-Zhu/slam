"""Record, orderly close, inspect and actually replay mock ROS messages."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import uuid
from collections import Counter
from pathlib import Path

import rclpy
import rosbag2_py
from dogzilla_device_capture.node import CaptureNode, snapshot_qos, stream_qos
from rclpy.context import Context
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.serialization import deserialize_message

from dogzilla_capture_interfaces.msg import (
    CaptureEvent,
    CaptureMetadata,
    CaptureStatus,
    Feedback,
)
from dogzilla_capture_interfaces.srv import SubmitMotion


def spin_until(
    executor: MultiThreadedExecutor, condition, timeout: float = 8.0
) -> None:
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.02)
    assert condition(), "ROS bag test timed out"


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
            raise AssertionError("rosbag did not stop orderly") from None


def test_mock_record_close_and_replay(tmp_path: Path) -> None:
    context = Context()
    rclpy.init(context=context)
    namespace = "/capture_bag_" + uuid.uuid4().hex[:8]
    entry = CaptureNode(
        context=context,
        namespace=namespace,
        parameter_overrides=[
            Parameter("backend", value="mock"),
            Parameter("enable_motion", value=True),
        ],
    )
    observer = rclpy.create_node(
        "bag_observer_" + uuid.uuid4().hex[:8], context=context
    )
    executor = MultiThreadedExecutor(num_threads=4, context=context)
    executor.add_node(entry)
    executor.add_node(observer)
    types = {
        "feedback": Feedback,
        "events": CaptureEvent,
        "status": CaptureStatus,
        "metadata": CaptureMetadata,
    }
    topics = {namespace + "/" + name: cls for name, cls in types.items()}
    bag = tmp_path / "recording"
    qos = tmp_path / "qos.yaml"
    qos.write_text(
        "\n".join(
            f"{namespace}/{name}:\n  reliability: reliable\n  durability: {'transient_local' if name in ('metadata', 'status') else 'volatile'}\n  history: keep_last\n  depth: 1024"
            for name in types
        )
        + "\n"
    )
    record_log = tmp_path / "record.log"
    player_log = tmp_path / "play.log"
    recorder = None
    player = None
    entry_destroyed = False
    try:
        spin_until(
            executor,
            lambda: (
                entry.controller.status().state == "READY"
                and entry.controller.metadata().firmware is not None
            ),
        )
        with record_log.open("w") as output:
            recorder = subprocess.Popen(
                [
                    "ros2",
                    "bag",
                    "record",
                    "-o",
                    str(bag),
                    "--qos-profile-overrides-path",
                    str(qos),
                    *topics,
                ],
                stdout=output,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            spin_until(
                executor, lambda: entry._feedback_pub.get_subscription_count() >= 1
            )
            client = observer.create_client(SubmitMotion, namespace + "/submit_motion")
            assert client.wait_for_service(timeout_sec=3)
            future = client.call_async(
                SubmitMotion.Request(
                    session_id=entry.controller.status().session_id,
                    request_id="bag-motion",
                    action="left",
                    magnitude=30,
                    duration_s=0.15,
                )
            )
            spin_until(executor, future.done)
            assert future.result().accepted
            spin_until(executor, lambda: entry.controller.status().state == "READY")
            # Allow the publication timer and recorder to drain the finite action.
            end = time.monotonic() + 0.6
            while time.monotonic() < end:
                executor.spin_once(timeout_sec=0.02)
            stop_process(recorder)
        assert recorder.returncode == 0, record_log.read_text()
        assert (bag / "metadata.yaml").exists()
        reader = rosbag2_py.SequentialReader()
        reader.open(
            rosbag2_py.StorageOptions(uri=str(bag), storage_id="sqlite3"),
            rosbag2_py.ConverterOptions("", ""),
        )
        recorded = {name: [] for name in topics}
        while reader.has_next():
            topic, data, _stamp = reader.read_next()
            recorded[topic].append(deserialize_message(data, topics[topic]))
        expected = Counter(
            {topic: len(messages) for topic, messages in recorded.items()}
        )
        assert all(count > 0 for count in expected.values()), expected
        motion_written = next(
            item
            for item in recorded[namespace + "/events"]
            if item.kind == "MOTION_WRITTEN"
        )
        motion_detail = json.loads(motion_written.detail)
        assert motion_detail["action"] == "left"
        assert motion_detail["magnitude"] == 30
        assert motion_detail["duration_s"] == 0.15
        assert (
            motion_detail["deadline_mono_ns"] - motion_detail["motion_start_mono_ns"]
            == 150_000_000
        )
        assert any(
            item.kind == "STOP_WRITTEN" for item in recorded[namespace + "/events"]
        )
        assert any(
            item.has_firmware and item.firmware.text == "MOCK-ONLY"
            for item in recorded[namespace + "/metadata"]
        )
        assert all(
            item.mono_end_ns >= item.mono_start_ns
            for item in recorded[namespace + "/feedback"]
        )
        assert any(
            item.valid and item.chunks for item in recorded[namespace + "/feedback"]
        )
        # Remove the complete live entry: replay has no motion service receiver.
        assert entry.close()
        executor.remove_node(entry)
        entry.destroy_node()
        entry_destroyed = True
        spin_until(executor, lambda: not client.service_is_ready())
        observer.destroy_client(client)
        received = {name: [] for name in topics}
        subscriptions = []
        for topic, cls in topics.items():
            callback = received[topic].append
            playback_qos = (
                snapshot_qos()
                if topic.endswith(("/metadata", "/status"))
                else stream_qos()
            )
            playback_qos.depth = (
                1024  # Audit every recorded status, not only the latest state.
            )
            subscriptions.append(
                observer.create_subscription(cls, topic, callback, playback_qos)
            )
        with player_log.open("w") as output:
            player = subprocess.Popen(
                [
                    "ros2",
                    "bag",
                    "play",
                    str(bag),
                    "--delay",
                    "1",
                    "--qos-profile-overrides-path",
                    str(qos),
                ],
                stdout=output,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            spin_until(executor, lambda: player.poll() is not None, timeout=12)
            spin_until(
                executor,
                lambda: all(
                    len(received[topic]) >= count for topic, count in expected.items()
                ),
            )
        assert player.returncode == 0, player_log.read_text()
        assert (
            Counter({topic: len(messages) for topic, messages in received.items()})
            == expected
        )
        for topic in topics:
            if topic.endswith("/feedback"):
                assert [item.sequence for item in received[topic]] == [
                    item.sequence for item in recorded[topic]
                ]
                assert [list(item.values) for item in received[topic]] == [
                    list(item.values) for item in recorded[topic]
                ]
            elif topic.endswith("/events"):
                assert [
                    (item.kind, item.request_id, item.mono_ns)
                    for item in received[topic]
                ] == [
                    (item.kind, item.request_id, item.mono_ns)
                    for item in recorded[topic]
                ]
        assert entry.controller.status().state == "CLOSED"
    finally:
        if recorder is not None:
            stop_process(recorder)
        if player is not None:
            stop_process(player)
        if not entry_destroyed:
            entry.close()
        executor.shutdown(timeout_sec=3)
        if not entry_destroyed:
            entry.destroy_node()
        observer.destroy_node()
        rclpy.shutdown(context=context)
