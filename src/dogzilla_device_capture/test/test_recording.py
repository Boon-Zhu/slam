"""录包证据与失效边界；全部来源明确为合成数据。"""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import time

import pytest
from dogzilla_device_capture.recording import (
    RecordingLedger,
    Source,
    sources_from_config,
)


def test_readiness_requires_writer_receipt_and_matching_subscription():
    source = Source({"topic": "/scan", "type": "sensor_msgs/msg/LaserScan"})
    ledger = RecordingLedger([source])
    assert not ledger.snapshot()["ready"]
    ledger.created.add("/scan")
    ledger.matched["/scan"] = 1
    assert not ledger.snapshot()["ready"]
    ledger.written("/scan", 100, time.monotonic())
    assert ledger.snapshot()["ready"]
    assert ledger.counts["/scan"] == 1


def test_event_with_no_message_still_requires_matching_subscription():
    source = Source(
        {"topic": "/event", "type": "std_msgs/msg/String", "require_message": False}
    )
    ledger = RecordingLedger([source])
    ledger.created.add("/event")
    assert not ledger.snapshot()["ready"]
    ledger.matched["/event"] = 1
    result = ledger.snapshot(now=ledger.started_mono + 100)
    assert result["ready"]
    assert result["interrupted"] == []
    assert ledger.counts["/event"] == 0


def test_single_source_gap_keeps_counts_and_reports_recovery():
    sources = [
        Source({"topic": name, "type": "std_msgs/msg/String", "stale_after_sec": 1})
        for name in ("/a", "/b")
    ]
    ledger = RecordingLedger(sources)
    for source in sources:
        ledger.created.add(source.topic)
        ledger.matched[source.topic] = 1
        ledger.written(source.topic, 100, 10)
    ledger.written("/b", 200, 12)
    result = ledger.snapshot(now=12)
    assert result["interrupted"] == ["/a"]
    assert result["ready"]
    assert ledger.counts == {"/a": 1, "/b": 2}
    ledger.written("/a", 300, 12.1)
    assert ledger.snapshot(now=12.2)["interrupted"] == []
    assert ledger.interruptions[0]["recovered_wall_ns"] == 300


@pytest.mark.parametrize(
    "value",
    [
        {"topic": "relative", "type": "std_msgs/msg/String"},
        {"topic": "/a", "type": "String"},
        {"topic": "/a", "type": "std_msgs/msg/String", "stale_after_sec": float("nan")},
        {"topic": "/a", "type": "std_msgs/msg/String", "require_message": "false"},
        {"topic": "/a", "type": "std_msgs/msg/String", "reliability": "invalid"},
    ],
)
def test_source_rejects_invalid_boundary(value):
    with pytest.raises(ValueError):
        Source(value)


def test_duplicate_sources_rejected():
    source = {"topic": "/a", "type": "std_msgs/msg/String"}
    with pytest.raises(ValueError):
        sources_from_config({"sources": [source, source]})


def terminate(process):
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_health(path, process, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            health = json.loads(path.read_text())
            if predicate(health):
                return health
        assert process.poll() is None, f"worker exited {process.returncode}"
        time.sleep(0.1)
    raise AssertionError(
        f"health timeout: {path.read_text() if path.exists() else 'missing'}"
    )


@pytest.mark.parametrize("fail_write", [False, True])
def test_real_ros_recorder_closes_bag_and_matches_written_counts(tmp_path, fail_write):
    """实际 DDS + sqlite bag，mock 入口不访问任何硬件。"""
    namespace = "/recording_test_" + str(os.getpid())
    config = {
        "backend": "mock",
        "enable_motion": False,
        "namespace": namespace,
        "timeout_s": 10,
        "sources": [
            {
                "topic": namespace + "/status",
                "type": "dogzilla_capture_interfaces/msg/CaptureStatus",
                "latched": True,
            },
            {
                "topic": namespace + "/metadata",
                "type": "dogzilla_capture_interfaces/msg/CaptureMetadata",
                "latched": True,
            },
            {
                "topic": namespace + "/feedback",
                "type": "dogzilla_capture_interfaces/msg/Feedback",
            },
            {
                "topic": namespace + "/events",
                "type": "dogzilla_capture_interfaces/msg/CaptureEvent",
                "require_message": False,
            },
        ],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    env = dict(os.environ, ROS_LOCALHOST_ONLY="1")
    logs = (tmp_path / "entry.log").open("w")
    recorder_logs = (tmp_path / "recorder.log").open("w")
    entry = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "dogzilla_device_capture.node",
            "--ros-args",
            "-r",
            "__ns:=" + namespace,
            "-p",
            "backend:=mock",
            "-p",
            "enable_motion:=false",
        ],
        env=env,
        stdout=logs,
        stderr=subprocess.STDOUT,
    )
    recorder = None
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dogzilla_device_capture.recording",
                "probe",
                "--config",
                str(config_path),
                "--output",
                str(tmp_path / "probe.json"),
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert result.returncode == 0, (
            result.stdout + result.stderr + (tmp_path / "entry.log").read_text()
        )
        probe = json.loads((tmp_path / "probe.json").read_text())
        assert probe["ok"] and probe["firmware_valid"]
        assert not probe["missing_topics"]
        bag, health_path = tmp_path / "bag", tmp_path / "health.json"
        worker_command = [
            sys.executable,
            "-m",
            "dogzilla_device_capture.recording",
            "record",
            "--config",
            str(config_path),
            "--bag",
            str(bag),
            "--health",
            str(health_path),
        ]
        if fail_write:
            injected = """
import sys
from pathlib import Path
import rosbag2_py
from dogzilla_device_capture.recording import record, read_config
original = rosbag2_py.SequentialWriter
class FailingWriter:
    def __init__(self):
        self.inner = original()
    def __getattr__(self, name):
        return getattr(self.inner, name)
    def write(self, *args):
        raise OSError('synthetic injected disk write failure')
rosbag2_py.SequentialWriter = FailingWriter
raise SystemExit(record(read_config(Path(sys.argv[1])), Path(sys.argv[2]), Path(sys.argv[3])))
"""
            worker_command = [
                sys.executable,
                "-c",
                injected,
                str(config_path),
                str(bag),
                str(health_path),
            ]
        recorder = subprocess.Popen(
            worker_command, env=env, stdout=recorder_logs, stderr=subprocess.STDOUT
        )
        if fail_write:
            assert recorder.wait(timeout=15) != 0
            health = json.loads(health_path.read_text())
            assert "synthetic injected disk write failure" in health["fatal"]
            assert not health["ready"]
            assert all(item["count"] == 0 for item in health["sources"].values())
            return
        health = wait_health(health_path, recorder, lambda value: value["ready"])
        assert all(item["subscription_created"] for item in health["sources"].values())
        terminate(recorder)
        assert recorder.returncode == 0, (tmp_path / "recorder.log").read_text()
        health = json.loads(health_path.read_text())
        assert health["closed"] and not health["fatal"]
        assert (bag / "metadata.yaml").is_file()
        with sqlite3.connect(next(bag.glob("*.db3"))) as connection:
            actual = dict(
                connection.execute(
                    "SELECT topics.name, count(messages.id) FROM topics LEFT JOIN messages ON topics.id=messages.topic_id GROUP BY topics.name"
                )
            )
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert actual == {
            topic: item["count"] for topic, item in health["sources"].items()
        }
        assert actual[namespace + "/feedback"] > 0
    finally:
        if recorder is not None:
            terminate(recorder)
        terminate(entry)
        logs.close()
        recorder_logs.close()
