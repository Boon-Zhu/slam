"""录包自身的收录证据及 ROS 探查边界；不向设备下发运动。"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import io
import json
import math
import os
import signal
import sys
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any


class Source:
    """已校验的话题与中断检测配置。"""

    def __init__(self, value: object) -> None:
        if not isinstance(value, dict):
            raise ValueError("source 必须为对象")
        topic = value.get("topic")
        message_type = value.get("type")
        if not isinstance(topic, str) or not topic.startswith("/"):
            raise ValueError("source.topic 必须为绝对 ROS 名称")
        if not isinstance(message_type, str) or "/msg/" not in message_type:
            raise ValueError("source.type 必须为 package/msg/Type")
        self.topic = topic
        self.type = message_type
        self.reliability = value.get(
            "reliability",
            "best_effort" if self.type.startswith("sensor_msgs/") else "reliable",
        )
        if self.reliability not in ("reliable", "best_effort"):
            raise ValueError("reliability 必须为 reliable 或 best_effort")
        self.latched = value.get("latched", False)
        self.required = value.get("required", True)
        self.require_message = value.get("require_message", True)
        if not all(
            type(v) is bool for v in (self.latched, self.required, self.require_message)
        ):
            raise ValueError("source 布尔配置类型错误")
        seconds = value.get("stale_after_sec", 5.0)
        if isinstance(seconds, bool) or not isinstance(seconds, (float, int)):
            raise ValueError("stale_after_sec 必须为正数")
        self.stale_after_sec = float(seconds)
        if not math.isfinite(self.stale_after_sec) or self.stale_after_sec <= 0:
            raise ValueError("stale_after_sec 必须为有限正数")


def read_config(path: Path) -> dict[str, Any]:
    """JSON 是运行时配置边界，ROS 类型只在适配层动态解析。"""
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("config 必须为 JSON 对象")
    return value


def sources_from_config(config: dict[str, Any]) -> list[Source]:
    values = config.get("sources")
    if not isinstance(values, list) or not values:
        raise ValueError("sources 必须为非空数组")
    sources = [Source(value) for value in values]
    if len({source.topic for source in sources}) != len(sources):
        raise ValueError("sources 不允许重复话题")
    return sources


def atomic_json(path: Path, value: object) -> None:
    """原子替换并 fsync 文件，读者不会看到部分 JSON。"""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class RecordingLedger:
    """仅记已成功交给 writer 的消息；中断不触发停车。"""

    def __init__(self, sources: list[Source]) -> None:
        self.sources = sources
        self.counts = dict.fromkeys((source.topic for source in sources), 0)
        self.first_wall: dict[str, int] = {}
        self.last_wall: dict[str, int] = {}
        self.last_mono: dict[str, float] = {}
        self.matched: dict[str, int] = {}
        self.created: set[str] = set()
        self.interruptions: list[dict[str, object]] = []
        self.open_interruptions: dict[str, dict[str, object]] = {}
        self.started_mono = time.monotonic()

    def written(self, topic: str, wall_ns: int, mono: float) -> None:
        self.counts[topic] += 1
        self.first_wall.setdefault(topic, wall_ns)
        self.last_wall[topic] = wall_ns
        self.last_mono[topic] = mono
        gap = self.open_interruptions.pop(topic, None)
        if gap is not None:
            gap["recovered_wall_ns"] = wall_ns
            gap["recovered_mono"] = mono

    def snapshot(self, now: float | None = None) -> dict[str, object]:
        now = time.monotonic() if now is None else now
        topics: dict[str, object] = {}
        waiting: list[str] = []
        interrupted: list[str] = []
        for source in self.sources:
            topic = source.topic
            matched = self.matched.get(topic, 0)
            ready = (
                topic in self.created
                and matched > 0
                and (not source.require_message or self.counts[topic] > 0)
            )
            if not ready:
                waiting.append(topic)
            # 快照及事件不是周期源；不能因未出现新事件宣称中断。
            stale = bool(
                source.require_message
                and not source.latched
                and (
                    now - self.last_mono.get(topic, self.started_mono)
                    > source.stale_after_sec
                )
            )
            if stale:
                interrupted.append(topic)
                if topic not in self.open_interruptions:
                    gap: dict[str, object] = {
                        "topic": topic,
                        "detected_wall_ns": time.time_ns(),
                        "last_written_wall_ns": self.last_wall.get(topic),
                        "detected_mono": now,
                        "recovered_wall_ns": None,
                    }
                    self.open_interruptions[topic] = gap
                    self.interruptions.append(gap)
            topics[topic] = {
                "type": source.type,
                "subscription_created": topic in self.created,
                "matched_publishers": matched,
                "count": self.counts[topic],
                "first_wall_ns": self.first_wall.get(topic),
                "last_wall_ns": self.last_wall.get(topic),
                "require_message": source.require_message,
                "ready": ready,
                "interrupted": stale,
            }
        return {
            "ready": not waiting,
            "waiting": waiting,
            "sources": topics,
            "interrupted": interrupted,
            "interruptions": self.interruptions,
            "warnings": [
                {"kind": "source_interrupted", "topic": topic} for topic in interrupted
            ],
            "updated_wall_ns": time.time_ns(),
            "updated_mono": now,
            "evidence": "recorder subscription and successful SequentialWriter.write; final durability checked after close",
        }


def source_qos(source: Source) -> Any:
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # type: ignore[import-untyped]

    return QoSProfile(
        depth=1024,
        reliability=ReliabilityPolicy.RELIABLE
        if source.reliability == "reliable"
        else ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.TRANSIENT_LOCAL
        if source.latched
        else DurabilityPolicy.VOLATILE,
    )


@lru_cache(maxsize=1)
def _rcl_library() -> Any:
    library = ctypes.CDLL("librcl.so")
    library.rcl_subscription_get_publisher_count.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    library.rcl_subscription_get_publisher_count.restype = ctypes.c_int
    return library


def matched_publishers(subscription: Any) -> int:
    """Humble 无 Python 匹配计数；使用原版 rcl 的公开 C API。"""
    count = ctypes.c_size_t()
    with subscription.handle:
        code = _rcl_library().rcl_subscription_get_publisher_count(
            ctypes.c_void_p(subscription.handle.pointer), ctypes.byref(count)
        )
    if code != 0:
        raise RuntimeError(f"rcl_subscription_get_publisher_count failed: {code}")
    return count.value


def discover_topics(node: Any) -> list[dict[str, object]]:
    """给编排层提供所有有发布者的话题；不静默裁剪其他实际来源。"""
    from rclpy.qos import DurabilityPolicy, ReliabilityPolicy

    result: list[dict[str, object]] = []
    for topic, types in node.get_topic_names_and_types():
        publishers = node.get_publishers_info_by_topic(topic)
        if not publishers:
            continue
        result.append(
            {
                "topic": topic,
                "types": types,
                "type": types[0] if len(types) == 1 else None,
                "publisher_count": len(publishers),
                "latched": all(
                    p.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL
                    for p in publishers
                ),
                "reliability": "best_effort"
                if any(
                    p.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
                    for p in publishers
                )
                else "reliable",
                "publishers": [
                    {
                        "node": p.node_namespace + "/" + p.node_name,
                        "type": p.topic_type,
                        "durability": str(p.qos_profile.durability),
                        "reliability": str(p.qos_profile.reliability),
                    }
                    for p in publishers
                ],
            }
        )
    return result


def record(config: dict[str, Any], bag: Path, health: Path) -> int:
    import rclpy  # type: ignore[import-untyped]
    import rosbag2_py  # type: ignore[import-untyped]
    from rclpy.signals import SignalHandlerOptions  # type: ignore[import-untyped]
    from rosidl_runtime_py.utilities import get_message  # type: ignore[import-untyped]

    sources = sources_from_config(config)
    ledger = RecordingLedger(sources)
    stopped = False
    fatal = ""
    closed = False
    node: Any = None
    writer: Any = None
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}

    def stop_signal(_signum: int, _frame: object) -> None:
        nonlocal stopped
        stopped = True

    rclpy.init(args=[], signal_handler_options=SignalHandlerOptions.NO)
    for sig in previous:
        signal.signal(sig, stop_signal)
    try:
        if bag.exists():
            raise FileExistsError(f"拒绝覆盖 bag: {bag}")
        writer = rosbag2_py.SequentialWriter()
        writer.open(
            rosbag2_py.StorageOptions(uri=str(bag), storage_id="sqlite3"),
            rosbag2_py.ConverterOptions("cdr", "cdr"),
        )
        node = rclpy.create_node("capture_recorder_" + uuid.uuid4().hex[:8])
        subscriptions: dict[str, Any] = {}

        def callback_for(topic: str) -> Any:
            def receive(data: bytes) -> None:
                nonlocal fatal, stopped
                if stopped:
                    return
                wall_ns = time.time_ns()
                try:
                    writer.write(topic, data, wall_ns)
                except Exception as exc:
                    fatal = f"writer.write {topic}: {type(exc).__name__}: {exc}"
                    stopped = True
                    raise
                ledger.written(topic, wall_ns, time.monotonic())

            return receive

        for source in sources:
            writer.create_topic(
                rosbag2_py.TopicMetadata(
                    name=source.topic, type=source.type, serialization_format="cdr"
                )
            )
            subscriptions[source.topic] = node.create_subscription(
                get_message(source.type),
                source.topic,
                callback_for(source.topic),
                source_qos(source),
                raw=True,
            )
            ledger.created.add(source.topic)
        last_report = 0.0
        while rclpy.ok() and not stopped:
            rclpy.spin_once(node, timeout_sec=0.1)
            if time.monotonic() - last_report < 0.5:
                continue
            last_report = time.monotonic()
            for topic, subscription in subscriptions.items():
                ledger.matched[topic] = matched_publishers(subscription)
            report = ledger.snapshot()
            report.update({"fatal": fatal, "closed": False, "pid": os.getpid()})
            atomic_json(health, report)
    except Exception as exc:
        fatal = fatal or f"{type(exc).__name__}: {exc}"
        print(fatal, file=sys.stderr, flush=True)
    finally:
        # Humble 的公开 Python API 无 close；销毁 writer 同步写 metadata。
        # 不在 callback 闭包之外保留 writer 对象引用。
        writer = None
        closed = bag.joinpath("metadata.yaml").is_file()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        report = ledger.snapshot()
        report.update({"fatal": fatal, "closed": closed, "pid": os.getpid()})
        try:
            atomic_json(health, report)
        except OSError as exc:
            print(f"无法保存 recorder health: {exc}", file=sys.stderr, flush=True)
            fatal = fatal or str(exc)
    return 0 if not fatal and closed else 1


def probe(config: dict[str, Any]) -> dict[str, object]:
    import rclpy
    from rosidl_runtime_py.utilities import get_message

    from dogzilla_capture_interfaces.msg import CaptureMetadata, CaptureStatus  # type: ignore[import-untyped]

    from .node import snapshot_qos

    sources = sources_from_config(config)
    timeout_s = float(config.get("timeout_s", 10.0))
    namespace = str(config.get("namespace", "/capture/device"))
    rclpy.init(args=[])
    node = rclpy.create_node("capture_probe_" + uuid.uuid4().hex[:8])
    statuses: list[Any] = []
    metadata: list[Any] = []
    counts = dict.fromkeys((source.topic for source in sources), 0)
    subscriptions: dict[str, Any] = {}

    def count_for(topic: str) -> Any:
        def receive(_data: bytes) -> None:
            counts[topic] += 1

        return receive

    try:
        node.create_subscription(
            CaptureStatus, namespace + "/status", statuses.append, snapshot_qos()
        )
        node.create_subscription(
            CaptureMetadata, namespace + "/metadata", metadata.append, snapshot_qos()
        )
        for source in sources:
            subscriptions[source.topic] = node.create_subscription(
                get_message(source.type),
                source.topic,
                count_for(source.topic),
                source_qos(source),
                raw=True,
            )
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if (
                len(statuses) >= 2
                and metadata
                and all(
                    matched_publishers(subscriptions[source.topic]) > 0
                    and (counts[source.topic] > 0 or not source.require_message)
                    for source in sources
                )
            ):
                break
        source_results = {
            source.topic: {
                "available": matched_publishers(subscriptions[source.topic]) > 0
                and (counts[source.topic] > 0 or not source.require_message),
                "type": source.type,
                "observed_messages": counts[source.topic],
                "matched_publishers": matched_publishers(subscriptions[source.topic]),
                "evidence": "preparation observer, not recorder evidence",
            }
            for source in sources
        }
        result: dict[str, object] = {
            "ok": False,
            "backend": "unknown",
            "enable_motion": None,
            "state": "UNKNOWN",
            "current_request_id": "unknown",
            "pending_request_id": "unknown",
            "active_request_id": "unknown",
            "firmware_valid": False,
            "session_id": "",
            "sources": source_results,
            "discovered_topics": discover_topics(node),
            "wall_ns": time.time_ns(),
            "missing_topics": [
                topic
                for topic, value in source_results.items()
                if not value["available"]
            ],
        }
        if not statuses or not metadata:
            result["error"] = "未收到入口状态或 metadata"
            return result
        state = statuses[-1]
        meta = metadata[-1]
        entries = dict(zip(meta.keys, meta.values))
        backend = entries.get("backend", "unknown")
        firmware_valid = bool(meta.has_firmware and meta.firmware.valid)
        fresh = (
            len(statuses) >= 2 and abs(time.time_ns() - state.wall_ns) < timeout_s * 1e9
        )
        same_session = state.session_id == meta.session_id
        result.update(
            {
                "backend": backend,
                "enable_motion": state.enable_motion,
                "state": state.state,
                "current_request_id": state.current_request_id,
                # 当前接口合并 pending/current；两项保守报告，绝不推断为空。
                "pending_request_id": state.current_request_id,
                "active_request_id": state.current_request_id,
                "firmware_valid": firmware_valid,
                "session_id": state.session_id,
                "metadata": entries,
                "status_fresh": fresh,
                "ok": bool(
                    fresh
                    and same_session
                    and firmware_valid
                    and state.state == "READY"
                    and backend == config.get("backend", "vendor")
                    and state.enable_motion == config.get("enable_motion", False)
                ),
            }
        )
        return result
    finally:
        node.destroy_node()
        rclpy.shutdown()


def stop(config: dict[str, Any]) -> dict[str, object]:
    """复用 capturectl 一次请求和事件确认逻辑；结果未知时不重发。"""
    import rclpy

    from .cli import run_command
    from .cli_arguments import Arguments

    rclpy.init(args=[])
    node = rclpy.create_node("capture_failure_stop_" + uuid.uuid4().hex[:8])
    output, errors = io.StringIO(), io.StringIO()
    code = 3
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = run_command(
                node,
                Arguments(
                    "stop",
                    str(config.get("namespace", "/capture/device")),
                    float(config.get("timeout_s", 10.0)),
                ),
            )
    except Exception as exc:
        errors.write(f"{type(exc).__name__}: {exc}")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return {
        "returncode": code,
        "stdout": output.getvalue(),
        "stderr": errors.getvalue(),
        "physical_state": "not_verified",
        "wall_ns": time.time_ns(),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("probe", "record", "stop"):
        command = sub.add_parser(name)
        command.add_argument("--config", type=Path, required=True)
        if name == "record":
            command.add_argument("--bag", type=Path, required=True)
            command.add_argument("--health", type=Path, required=True)
        else:
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    config = read_config(args.config)
    if args.command == "record":
        raise SystemExit(record(config, args.bag, args.health))
    result = probe(config) if args.command == "probe" else stop(config)
    atomic_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result.get("ok", result.get("returncode") == 0) else 1)


if __name__ == "__main__":
    main()
