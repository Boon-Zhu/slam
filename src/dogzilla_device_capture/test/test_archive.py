"""导出完整性、禁止覆盖和异常 bag 的无硬件边界验证。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
import yaml
from dogzilla_device_capture.archive import (
    ArchiveError,
    export_round,
    inspect_bag,
    seal_round,
    verify_export,
)
from dogzilla_device_capture.round_session import clean


def make_round(root: Path, state: str = "finished") -> Path:
    current = root / "current"
    current.mkdir()
    (current / "round.json").write_text(
        json.dumps({"round_id": "test-round-01", "state": state})
    )
    (current / "evidence.log").write_text("SYNTHETIC TEST ONLY\n")
    return current


def make_bag(root: Path) -> Path:
    bag = root / "bag"
    bag.mkdir()
    with sqlite3.connect(bag / "bag_0.db3") as db:
        db.execute("CREATE TABLE topics(id INTEGER PRIMARY KEY,name TEXT,type TEXT)")
        db.execute(
            "CREATE TABLE messages(id INTEGER PRIMARY KEY,topic_id INTEGER,timestamp INTEGER,data BLOB)"
        )
        db.execute("INSERT INTO topics VALUES(1,'/scan','sensor_msgs/msg/LaserScan')")
        db.executemany(
            "INSERT INTO messages VALUES(?,?,?,?)",
            [(1, 1, 100, b"abcd"), (2, 1, 200, b"efgh")],
        )
    (bag / "metadata.yaml").write_text(
        yaml.safe_dump(
            {
                "rosbag2_bagfile_information": {
                    "storage_identifier": "sqlite3",
                    "relative_file_paths": ["bag_0.db3"],
                    "message_count": 2,
                    "topics_with_message_count": [
                        {"topic_metadata": {"name": "/scan"}, "message_count": 2}
                    ],
                }
            }
        )
    )
    return bag


def test_export_verified_independent_and_no_overwrite(tmp_path: Path) -> None:
    current = make_round(tmp_path)
    seal_round(current)
    exported = export_round(current, tmp_path / "computer")
    receipt = verify_export(exported)
    assert receipt["ok"] and not receipt["replay_verified"]
    assert receipt["exported"]
    assert not verify_export(current, write_report=False)["exported"]
    assert receipt["round_id"] == "test-round-01"
    assert (
        receipt["manifest_sha256"]
        == verify_export(current, write_report=False)["manifest_sha256"]
    )
    with pytest.raises(ArchiveError, match="拒绝覆盖"):
        export_round(current, tmp_path / "computer")
    assert (
        current.joinpath("evidence.log").read_text()
        == exported.joinpath("evidence.log").read_text()
    )


@pytest.mark.parametrize("mutation", ["changed", "added", "missing"])
def test_corrupt_export_is_rejected(tmp_path: Path, mutation: str) -> None:
    current = make_round(tmp_path)
    seal_round(current)
    exported = export_round(current, tmp_path / "computer")
    if mutation == "changed":
        (exported / "evidence.log").write_text("damaged")
    elif mutation == "missing":
        (exported / "evidence.log").unlink()
    else:
        (exported / "unexpected").write_text("unexpected")
    with pytest.raises(ArchiveError, match="核对失败"):
        verify_export(exported)
    receipt = exported / "verification" / "export_receipt.json"
    assert json.loads(receipt.read_text())["ok"] is False
    with pytest.raises(RuntimeError, match="禁止清理"):
        clean(tmp_path, receipt)
    assert current.exists()
    assert verify_export(current, write_report=False)["ok"]


def test_invalid_manifest_revokes_receipt_before_validation(tmp_path: Path) -> None:
    current = make_round(tmp_path)
    seal_round(current)
    exported = export_round(current, tmp_path / "computer")
    receipt = exported / "verification" / "export_receipt.json"
    manifest = exported / "manifest.json"
    original = manifest.read_bytes()
    manifest.write_text("broken JSON")
    with pytest.raises(ValueError):
        verify_export(exported)
    assert json.loads(receipt.read_text())["ok"] is False
    with pytest.raises(RuntimeError, match="禁止清理"):
        clean(tmp_path, receipt)
    manifest.write_bytes(original)
    assert verify_export(exported)["ok"]
    assert clean(tmp_path, receipt)["ok"]
    assert not current.exists()
    assert (exported / "evidence.log").exists()


def test_receipt_write_failure_does_not_leave_old_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from dogzilla_device_capture import archive

    current = make_round(tmp_path)
    seal_round(current)
    exported = export_round(current, tmp_path / "computer")
    receipt = exported / "verification" / "export_receipt.json"

    def fail_write(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(archive, "_write_json", fail_write)
    with pytest.raises(OSError, match="disk full"):
        verify_export(exported)
    assert not receipt.exists()
    with pytest.raises(FileNotFoundError):
        clean(tmp_path, receipt)
    assert current.exists()


def test_live_round_cannot_seal_or_export(tmp_path: Path) -> None:
    current = make_round(tmp_path, "recording")
    with pytest.raises(ArchiveError, match="尚未关闭"):
        seal_round(current)
    with pytest.raises(FileNotFoundError):
        export_round(current, tmp_path / "computer")


def test_failed_round_preserved_and_exportable(tmp_path: Path) -> None:
    current = make_round(tmp_path, "failed")
    (current / "incomplete.db3").write_bytes(b"not a bag")
    seal_round(current)
    exported = export_round(current, tmp_path / "computer")
    assert (exported / "incomplete.db3").read_bytes() == b"not a bag"
    assert verify_export(exported)["ok"]


def test_manifest_cannot_escape_root_or_hide_evidence(tmp_path: Path) -> None:
    current = make_round(tmp_path)
    manifest = seal_round(current)
    manifest["files"]["../outside"] = {"size": 1, "sha256": "bad"}
    (current / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ArchiveError, match="非法相对路径"):
        verify_export(current)


def test_symlink_is_not_exported(tmp_path: Path) -> None:
    current = make_round(tmp_path)
    (current / "linked.log").symlink_to(current / "evidence.log")
    with pytest.raises(ArchiveError, match="符号链接"):
        seal_round(current)


def test_destination_inside_source_rejected(tmp_path: Path) -> None:
    current = make_round(tmp_path)
    seal_round(current)
    with pytest.raises(ArchiveError, match="内部"):
        export_round(current, current / "computer")


def test_bag_count_readability_and_coverage_separate(tmp_path: Path) -> None:
    bag = make_bag(tmp_path)
    report = inspect_bag(bag, ["/scan"])
    assert report["ok"] and report["message_count"] == 2
    assert report["topics"]["/scan"]["first_recorded_ns"] == 100
    missing = inspect_bag(bag, ["/scan", "/camera"])
    assert missing["readable"] and not missing["ok"]
    assert missing["missing_topics"] == ["/camera"]


def test_bag_metadata_mismatch_and_unlisted_file_fail(tmp_path: Path) -> None:
    bag = make_bag(tmp_path)
    with sqlite3.connect(bag / "bag_0.db3") as db:
        db.execute("DELETE FROM messages WHERE id=2")
    report = inspect_bag(bag, ["/scan"])
    assert not report["ok"] and "数量不一致" in report["errors"][0]
    (bag / "other.db3").write_bytes(b"unexpected")
    report = inspect_bag(bag, ["/scan"])
    assert not report["ok"] and "清单" in report["errors"][0]


def test_bag_invalid_and_path_escape_fail(tmp_path: Path) -> None:
    bag = make_bag(tmp_path)
    (bag / "bag_0.db3").write_bytes(b"broken")
    assert not inspect_bag(bag, ["/scan"])["ok"]
    content = yaml.safe_load((bag / "metadata.yaml").read_text())
    content["rosbag2_bagfile_information"]["relative_file_paths"] = ["../outside.db3"]
    (bag / "metadata.yaml").write_text(yaml.safe_dump(content))
    assert "非法相对路径" in inspect_bag(bag, ["/scan"])["errors"][0]


def test_actual_replay_checks_all_messages_and_content(tmp_path: Path) -> None:
    import time

    import rosbag2_py
    from dogzilla_device_capture.archive import replay_export
    from geometry_msgs.msg import PointStamped
    from rcl_interfaces.msg import ParameterEvent
    from rclpy.serialization import serialize_message

    current = make_round(tmp_path)
    writer = rosbag2_py.SequentialWriter()
    writer.open(
        rosbag2_py.StorageOptions(uri=str(current / "bag"), storage_id="sqlite3"),
        rosbag2_py.ConverterOptions("", ""),
    )
    writer.create_topic(
        rosbag2_py.TopicMetadata(
            name="/archive_synthetic_test",
            type="geometry_msgs/msg/PointStamped",
            serialization_format="cdr",
        )
    )
    writer.create_topic(
        rosbag2_py.TopicMetadata(
            name="/parameter_events",
            type="rcl_interfaces/msg/ParameterEvent",
            serialization_format="cdr",
        )
    )
    writer.create_topic(
        rosbag2_py.TopicMetadata(
            name="/rosout",
            type="rcl_interfaces/msg/Log",
            serialization_format="cdr",
        )
    )
    stamp = time.time_ns()
    for index in range(3):
        point = PointStamped()
        point.header.frame_id = "SYNTHETIC_ONLY"
        point.header.stamp.sec = 123
        point.header.stamp.nanosec = index * 100_000_000
        point.point.x = float(index)
        writer.write(
            "/archive_synthetic_test",
            serialize_message(point),
            stamp + index * 100_000_000,
        )
    event = ParameterEvent(node="/synthetic_source")
    event.stamp.sec = 123
    writer.write("/parameter_events", serialize_message(event), stamp + 300_000_000)
    del writer
    assert inspect_bag(current / "bag", ["/archive_synthetic_test"])["ok"]
    seal_round(current)
    exported = export_round(current, tmp_path / "computer")
    result = replay_export(exported, timeout_s=20)
    assert result["ok"], result
    assert result["topics"]["/archive_synthetic_test"]["received_count"] == 3
    assert result["topics"]["/archive_synthetic_test"][
        "content_and_embedded_timestamps_match"
    ]
    assert result["topics"]["/parameter_events"]["received_count"] == 1
    assert result["topics"]["/parameter_events"][
        "content_and_embedded_timestamps_match"
    ]
    # 播放器自身的参数事件可能在 DDS 发现前已经发出；不要求收到这些非录包数据。
    assert verify_export(exported, write_report=False)["ok"]
