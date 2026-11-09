"""采集轮次配置边界；真实配置必须显式给出校时、部署及设备证据。"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

Json = dict[str, Any]


def read_json(path: Path) -> Json:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Json) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_config(config: Json, synthetic: bool) -> None:
    if config.get("synthetic") is not synthetic:
        raise ValueError("synthetic 配置必须与显式 --synthetic 匹配")
    for name in ("timeout_s", "minimum_free_bytes"):
        value = config.get(name)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{name} 必须显式设置为正数；应依据部署实测确定")
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources 必须为非空列表")
    topics = []
    for source in sources:
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("topic"), str)
            or not isinstance(source.get("type"), str)
        ):
            raise ValueError("每个来源须有 topic/type")
        topics.append(source["topic"])
        stale = source.get("stale_after_sec", 0)
        if (
            not isinstance(stale, (int, float))
            or not math.isfinite(stale)
            or stale <= 0
        ):
            raise ValueError("stale_after_sec 必须为正数；latched及事件不检测陈旧")
    if len(topics) != len(set(topics)):
        raise ValueError("来源话题不可重复")
    namespace = config.get("namespace", "/capture/device")
    for suffix in ("status", "metadata", "feedback", "events"):
        if namespace + "/" + suffix not in topics:
            raise ValueError(f"缺少原始入口来源 {suffix}")
    drivers = config.get("drivers")
    if not isinstance(drivers, list) or not drivers:
        raise ValueError("drivers 不能为空")
    for driver in drivers:
        if not isinstance(driver, dict) or not isinstance(driver.get("name"), str):
            raise ValueError("driver 需具名")
        argv(driver.get("command"))
    if len({driver["name"] for driver in drivers}) != len(drivers):
        raise ValueError("driver name 不可重复")
    if any(not driver["name"].replace("_", "").isalnum() for driver in drivers):
        raise ValueError("driver name 仅允许字母数字下划线")
    if not synthetic:
        clock = config.get("clock", {})
        argv(clock.get("sync_command"))
        argv(clock.get("verify_command"))
        if not isinstance(clock.get("max_offset_s"), (float, int)) or not 0 < clock[
            "max_offset_s"
        ] < float("inf"):
            raise ValueError("真实配置须指定经部署确定的 clock.max_offset_s")
        deployment = config.get("deployment", {})
        if not deployment.get("expected_files") or not deployment.get("expected_image"):
            raise ValueError("真实配置须固定部署文件哈希和实际镜像标识")
        argv(deployment.get("environment_command"))
        if not config.get("devices"):
            raise ValueError("真实配置须显式列出需核对所有权/释放的设备路径")


def argv(value: object) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ValueError("命令必须为非空 argv 字符串数组，不执行隐式 shell")
    return list(value)


def snapshot_deployment(current: Path, expected_files: dict[str, str]) -> Json:
    """保存实际部署文件内容及映射，不仅交付无法复原参数的哈希。"""
    files: Json = {}
    destination = current / "deployment_files"
    if expected_files:
        destination.mkdir()
    for index, (filename, expected) in enumerate(expected_files.items()):
        source = Path(filename)
        actual = sha256(source)
        if actual != expected:
            raise RuntimeError(f"部署哈希不匹配: {filename}")
        snapshot = destination / f"{index:03d}-{source.name}"
        shutil.copyfile(source, snapshot)
        if sha256(snapshot) != actual:
            raise RuntimeError(f"部署文件在复制时发生变化: {filename}")
        files[filename] = {
            "sha256": actual,
            "snapshot": str(snapshot.relative_to(current)),
        }
    return files
