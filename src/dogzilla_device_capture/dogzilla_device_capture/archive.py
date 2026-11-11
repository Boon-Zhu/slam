"""关闭后的录包检查、不可覆盖导出与真实 ROS 回放核对。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from collections import Counter
from functools import partial
from pathlib import Path
from typing import Any


class ArchiveError(RuntimeError):
    """保留现有证据并向调用者报告失败。"""


def _read_json(path: Path) -> dict[str, Any]:
    value: Any = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ArchiveError(f"不是 JSON 对象: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def file_sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _safe_child(root: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ArchiveError(f"非法相对路径: {name}")
    child = root / relative
    if child.is_symlink() or any(parent.is_symlink() for parent in child.parents):
        raise ArchiveError(f"拒绝符号链接: {child}")
    return child


def _files(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            relative.parts[0] == "verification"
            or relative.as_posix() == "manifest.json"
        ):
            continue
        if path.is_symlink():
            raise ArchiveError(f"采集证据不得使用符号链接: {path}")
        if path.is_file():
            result[relative.as_posix()] = {
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        elif not path.is_dir():
            raise ArchiveError(f"采集目录包含非普通文件: {path}")
    return result


def _round_id(current: Path) -> str:
    value = _read_json(current / "round.json")
    identity = str(value.get("round_id", value.get("id", "")))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", identity):
        raise ArchiveError("round.json 中轮次 ID 无效")
    return identity


def inspect_bag(bag: Path, expected_topics: list[str]) -> dict[str, Any]:
    """只读 SQLite 录包；文件完整性与预期来源覆盖分别记录。"""
    import yaml  # type: ignore[import-untyped]

    result: dict[str, Any] = {
        "ok": False,
        "readable": False,
        "topics": {},
        "missing_topics": [],
        "errors": [],
        "checked_at_ns": time.time_ns(),
    }
    counts: Counter[str] = Counter()
    try:
        metadata = yaml.safe_load((bag / "metadata.yaml").read_text())[
            "rosbag2_bagfile_information"
        ]
        if metadata["storage_identifier"] != "sqlite3":
            raise ArchiveError("当前检查器仅支持 sqlite3，不能把未检查存储声明为成功")
        relative_paths = metadata["relative_file_paths"]
        if not relative_paths or len(set(relative_paths)) != len(relative_paths):
            raise ArchiveError("metadata 的数据库清单为空或重复")
        listed = {_safe_child(bag, str(name)).resolve() for name in relative_paths}
        if listed != {path.resolve() for path in bag.glob("*.db3")}:
            raise ArchiveError("metadata 数据库清单与实际 .db3 不一致")
        for name in relative_paths:
            path = _safe_child(bag, str(name))
            with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                integrity = db.execute("PRAGMA integrity_check").fetchall()
                if integrity != [("ok",)]:
                    raise ArchiveError(f"SQLite 完整性失败: {integrity}")
                for topic, kind, count, first, last in db.execute(
                    "SELECT t.name,t.type,COUNT(m.id),MIN(m.timestamp),MAX(m.timestamp) "
                    "FROM topics t LEFT JOIN messages m ON t.id=m.topic_id GROUP BY t.id"
                ):
                    counts[topic] += count
                    previous = result["topics"].get(topic, {})
                    if previous and previous["type"] != kind:
                        raise ArchiveError(f"分卷消息类型变化: {topic}")
                    result["topics"][topic] = {
                        "type": kind,
                        "count": counts[topic],
                        "first_recorded_ns": min(
                            first, previous.get("first_recorded_ns", first)
                        )
                        if first is not None
                        else None,
                        "last_recorded_ns": max(
                            last, previous.get("last_recorded_ns", last)
                        )
                        if last is not None
                        else None,
                    }
                # 读取每个 payload，损坏页不能因只 COUNT 而漏过。
                for (payload,) in db.execute("SELECT data FROM messages"):
                    if not isinstance(payload, bytes) or len(payload) < 4:
                        raise ArchiveError("无效或截断的 CDR payload")
        declared = {
            item["topic_metadata"]["name"]: item["message_count"]
            for item in metadata["topics_with_message_count"]
        }
        if (
            dict(counts) != declared
            or sum(counts.values()) != metadata["message_count"]
        ):
            raise ArchiveError("metadata 与数据库消息数量不一致")
        result["readable"] = True
        result["message_count"] = sum(counts.values())
        result["missing_topics"] = [
            topic for topic in expected_topics if counts[topic] == 0
        ]
        result["ok"] = not result["missing_topics"] and result["message_count"] > 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        sqlite3.Error,
        ArchiveError,
        yaml.YAMLError,
    ) as exc:
        result["errors"].append(str(exc))
    return result


def seal_round(current: Path) -> dict[str, Any]:
    """调用方须先关闭后台与日志；封存后不得继续修改轮次内容。"""
    state = _read_json(current / "round.json").get("state", "")
    if state not in {
        "finished",
        "failed",
        "closed",
        "finished_with_errors",
        "prepare_failed",
    }:
        raise ArchiveError(f"轮次尚未关闭，不能封存: {state}")
    if (current / "manifest.json").exists():
        verify_export(current, write_report=False)
        return _read_json(current / "manifest.json")
    manifest = {
        "format_version": 1,
        "round_id": _round_id(current),
        "sealed_at_ns": time.time_ns(),
        "files": _files(current),
    }
    _write_json(current / "manifest.json", manifest)
    return manifest


def verify_export(directory: Path, *, write_report: bool = True) -> dict[str, Any]:
    """核对完整文件集合，不把哈希成功等同于回放或全量覆盖成功。"""
    receipt_path = directory / "verification" / "export_receipt.json"
    invalid_receipt = {
        "ok": False,
        "exported": False,
        "verified_directory": str(directory.resolve()),
        "verification_started_ns": time.time_ns(),
        "error": "verification incomplete",
    }
    # 先撤销旧成功凭据，即使此次检查异常退出，也不能继续沿用旧成功结果。
    if write_report:
        receipt_path.unlink(missing_ok=True)
        _write_json(receipt_path, invalid_receipt)
    try:
        receipt = _check_export(directory)
    except Exception as exc:
        if write_report:
            _write_json(receipt_path, {**invalid_receipt, "error": str(exc)})
        raise
    if write_report:
        _write_json(receipt_path, receipt)
    return receipt


def _check_export(directory: Path) -> dict[str, Any]:
    manifest_path = directory / "manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("format_version") != 1 or manifest.get("round_id") != _round_id(
        directory
    ):
        raise ArchiveError("manifest 版本或轮次不一致")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or not expected:
        raise ArchiveError("manifest 文件清单为空或无效")
    for name in expected:
        _safe_child(directory, name)
    actual = _files(directory)
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        added = sorted(set(actual) - set(expected))
        changed = sorted(
            name
            for name in set(actual) & set(expected)
            if actual[name] != expected[name]
        )
        raise ArchiveError(
            f"哈希/文件集合核对失败: missing={missing}, added={added}, changed={changed}"
        )
    receipt = {
        "ok": True,
        "round_id": manifest["round_id"],
        "manifest_sha256": file_sha256(manifest_path),
        "file_count": len(actual),
        "verified_at_ns": time.time_ns(),
        "verified_directory": str(directory.resolve()),
        "replay_verified": False,
        "exported": False,
    }
    origin_path = directory / "verification" / "export_origin.json"
    if origin_path.exists():
        origin = _read_json(origin_path)
        receipt["exported"] = (
            origin.get("round_id") == manifest["round_id"]
            and origin.get("manifest_sha256") == receipt["manifest_sha256"]
            and origin.get("source") != str(directory.resolve())
        )
    return receipt


def export_round(source: Path, destination_root: Path) -> Path:
    """本地复制路径供挂载或测试使用；中断副本保留且不会覆盖旧导出。"""
    verify_export(source, write_report=False)
    identity = _round_id(source)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / identity
    if destination.exists():
        raise ArchiveError(f"导出已存在，拒绝覆盖: {destination}")
    if (
        source.resolve() in destination_root.resolve().parents
        or source.resolve() == destination_root.resolve()
    ):
        raise ArchiveError("导出目的地不能位于原件内部")
    partial = destination_root / (".partial-" + identity + "-" + uuid.uuid4().hex)
    shutil.copytree(source, partial, symlinks=True)
    verify_export(partial, write_report=False)
    # 独占目的目录，避免两个并发导出互相替换。
    destination.mkdir()
    for child in partial.iterdir():
        child.rename(destination / child.name)
    partial.rmdir()
    _write_json(
        destination / "verification" / "export_origin.json",
        {
            "round_id": identity,
            "source": str(source.resolve()),
            "manifest_sha256": file_sha256(destination / "manifest.json"),
            "exported_at_ns": time.time_ns(),
            "transport": "local_copy",
        },
    )
    verify_export(destination)
    return destination


def export_remote(source: str, destination_root: Path) -> Path:
    """经 SSH 读取封存目录；不在机器人上运行动作或删除命令。"""
    match = re.fullmatch(r"([A-Za-z0-9_.@-]+):(/[^\n\r]*)", source)
    if match is None or match[1].startswith("-"):
        raise ArchiveError("远程来源必须为 user@host:/absolute/path")
    host, remote = match.groups()
    manifest_process = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            host,
            "cat -- " + shlex.quote(remote.rstrip("/") + "/manifest.json"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    manifest = json.loads(manifest_process.stdout)
    identity = str(manifest["round_id"])
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", identity):
        raise ArchiveError("远程轮次 ID 无效")
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / identity
    if destination.exists():
        raise ArchiveError(f"导出已存在，拒绝覆盖: {destination}")
    partial = destination_root / (".partial-" + identity + "-" + uuid.uuid4().hex)
    partial.mkdir()
    # 明确使用传统 SCP 协议，使远端 shell 引用语义确定；不解包远端 tar。
    subprocess.run(
        [
            "scp",
            "-O",
            "-p",
            "-r",
            "-o",
            "BatchMode=yes",
            host + ":" + shlex.quote(remote.rstrip("/") + "/."),
            str(partial),
        ],
        check=True,
    )
    if (partial / "manifest.json").read_bytes() != manifest_process.stdout.encode():
        raise ArchiveError("复制期间远端 manifest 改变；保留部分副本")
    verify_export(partial, write_report=False)
    destination.mkdir()
    for child in partial.iterdir():
        child.rename(destination / child.name)
    partial.rmdir()
    _write_json(
        destination / "verification" / "export_origin.json",
        {
            "round_id": identity,
            "source": source,
            "manifest_sha256": file_sha256(destination / "manifest.json"),
            "exported_at_ns": time.time_ns(),
            "transport": "ssh_scp",
        },
    )
    verify_export(destination)
    return destination


def replay_export(directory: Path, *, timeout_s: float = 3600.0) -> dict[str, Any]:
    """独有 topic 命名空间实际回放，逐 topic 比对所有 CDR 内容及数量。"""
    import rclpy  # type: ignore[import-untyped]
    import rosbag2_py  # type: ignore[import-untyped]
    from rclpy.context import Context  # type: ignore[import-untyped]
    from rclpy.executors import SingleThreadedExecutor  # type: ignore[import-untyped]
    from rclpy.qos import QoSProfile  # type: ignore[import-untyped]
    from rclpy.serialization import deserialize_message  # type: ignore[import-untyped]
    from rosidl_runtime_py.utilities import get_message  # type: ignore[import-untyped]

    verify_export(directory, write_report=False)
    bag = directory / "bag"
    report_dir = directory / "verification"
    report_dir.mkdir(exist_ok=True)
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(bag), storage_id="sqlite3"),
        rosbag2_py.ConverterOptions("", ""),
    )
    topics = {item.name: item.type for item in reader.get_all_topics_and_types()}
    expected_count: Counter[str] = Counter()
    actual_count: Counter[str] = Counter()
    expected_hash = {topic: hashlib.sha256() for topic in topics}
    actual_hash = {topic: hashlib.sha256() for topic in topics}
    while reader.has_next():
        topic, data, _stamp = reader.read_next()
        expected_count[topic] += 1
        expected_hash[topic].update(data)
    del reader
    if not sum(expected_count.values()):
        raise ArchiveError("空录包不能通过回放")
    environment = os.environ.copy()
    # 不向原始 topic 发布录制数据；不创建运动服务客户端。
    prefix = "/archive_replay_" + uuid.uuid4().hex
    player_name = "archive_player_" + uuid.uuid4().hex
    generated_system_count: Counter[str] = Counter()
    context = Context()
    rclpy.init(context=context)
    node = rclpy.create_node(
        "archive_replay_check_" + uuid.uuid4().hex[:8], context=context
    )
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(node)
    player: subprocess.Popen[bytes] | None = None
    subscriptions: list[Any] = []
    qos_path = report_dir / "replay_qos.yaml"
    qos_path.write_text(
        "".join(
            f"{topic}:\n  reliability: reliable\n  durability: volatile\n  history: keep_last\n  depth: 4096\n"
            for topic in topics
        )
    )

    def callback(topic: str, data: bytes) -> None:
        # 回放器自身也会发布系统事件，全局 topic remap 会一并改变其名称。
        # 只剔除由本次随机命名播放器产生的消息，数量和原因保留在报告中。
        if topic in {"/rosout", "/parameter_events"}:
            message = deserialize_message(data, get_message(topics[topic]))
            origin = message.name if topic == "/rosout" else message.node
            if origin in {player_name, "/" + player_name}:
                generated_system_count[topic] += 1
                return
        actual_count[topic] += 1
        actual_hash[topic].update(data)

    try:
        for topic, kind in topics.items():
            subscriptions.append(
                node.create_subscription(
                    get_message(kind),
                    prefix + topic,
                    partial(callback, topic),
                    QoSProfile(depth=4096),
                    raw=True,
                )
            )
        with (report_dir / "replay.log").open("wb") as output:
            player = subprocess.Popen(
                [
                    "ros2",
                    "bag",
                    "play",
                    str(bag),
                    "--delay",
                    "2",
                    "--wait-for-all-acked",
                    "5000",
                    "--log-level",
                    "fatal",
                    "--qos-profile-overrides-path",
                    str(qos_path),
                    "--remap",
                    "__node:=" + player_name,
                    *[f"{topic}:={prefix}{topic}" for topic in topics],
                ],
                stdout=output,
                stderr=subprocess.STDOUT,
                env=environment,
            )
            deadline = time.monotonic() + timeout_s
            observed_graph: dict[str, list[str]] = {}
            matched_publishers: dict[str, int] = {}
            graph_checked_at = 0.0
            finished_at: float | None = None
            while time.monotonic() < deadline:
                executor.spin_once(timeout_sec=0.05)
                if time.monotonic() - graph_checked_at > 0.5:
                    observed_graph.update(dict(node.get_topic_names_and_types()))
                    for topic in topics:
                        matched_publishers[topic] = max(
                            matched_publishers.get(topic, 0),
                            node.count_publishers(prefix + topic),
                        )
                    graph_checked_at = time.monotonic()
                if player.poll() is not None:
                    if finished_at is None:
                        finished_at = time.monotonic()
                    if time.monotonic() - finished_at > 2:
                        break
            if player.poll() is None:
                raise ArchiveError("实际回放超时；未声明回放通过")
        comparison = {
            topic: {
                "expected_count": expected_count[topic],
                "received_count": actual_count[topic],
                "content_and_embedded_timestamps_match": expected_hash[
                    topic
                ].hexdigest()
                == actual_hash[topic].hexdigest(),
            }
            for topic in topics
        }
        report = {
            "ok": player.returncode == 0
            and all(
                item["expected_count"] == item["received_count"]
                and item["content_and_embedded_timestamps_match"]
                for item in comparison.values()
            ),
            "round_id": _round_id(directory),
            "checked_at_ns": time.time_ns(),
            "player_returncode": player.returncode,
            "topics": comparison,
            "observed_graph": observed_graph,
            "matched_publishers": matched_publishers,
            "generated_player_system_messages_excluded": dict(generated_system_count),
            "scope": "实际 ROS 回放逐 topic CDR 内容含嵌入时间戳及数量；不证明采样时间语义或物理正确性",
        }
        _write_json(report_dir / "replay_report.json", report)
        return report
    except Exception as exc:
        _write_json(
            report_dir / "replay_report.json",
            {
                "ok": False,
                "round_id": _round_id(directory),
                "checked_at_ns": time.time_ns(),
                "error": str(exc),
            },
        )
        raise
    finally:
        if player is not None and player.poll() is None:
            player.send_signal(signal.SIGINT)
            try:
                player.wait(timeout=5)
            except subprocess.TimeoutExpired:
                player.kill()
                player.wait(timeout=5)
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown(context=context)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--source", required=True)
    export.add_argument("--destination", required=True, type=Path)
    for command in ("verify", "replay"):
        commands.add_parser(command).add_argument(
            "--directory", required=True, type=Path
        )
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            path = (
                export_remote(args.source, args.destination)
                if ":" in args.source
                else export_round(Path(args.source), args.destination)
            )
            result: dict[str, Any] = {
                "ok": True,
                "directory": str(path),
                "receipt": str(path / "verification" / "export_receipt.json"),
            }
        elif args.command == "verify":
            result = verify_export(args.directory)
        else:
            result = replay_export(args.directory)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, ArchiveError, subprocess.SubprocessError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
