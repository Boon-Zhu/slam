"""显式资源交接：记录原状态、执行配置的临时停止命令并核实释放。"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from .recording import atomic_json
from .round_config import Json, argv, read_json
from .round_session import device_holders


class HandoffError(RuntimeError):
    """交接失败或结果未知；证据保留，不自动重试或恢复厂商服务。"""


def _assert_no_round(root: Path) -> None:
    current = root / "current"
    if current.exists() or current.is_symlink():
        raise HandoffError("current 已存在；拒绝资源交接，不停止服务、不校时")


def _run(command: list[str], directory: Path, name: str, timeout_s: float) -> Json:
    evidence: Json = {
        "command": command,
        "started_wall_ns": time.time_ns(),
        "returncode": None,
        "timed_out": False,
    }
    process: subprocess.Popen[bytes] | None = None
    try:
        with (
            (directory / f"{name}.stdout.log").open("wb") as stdout,
            (directory / f"{name}.stderr.log").open("wb") as stderr,
        ):
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                evidence["returncode"] = process.wait(timeout=timeout_s)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                evidence["timed_out"] = isinstance(exc, subprocess.TimeoutExpired)
                evidence["error"] = type(exc).__name__ + ": outcome may be unknown"
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
                evidence["returncode"] = process.returncode
                raise HandoffError(f"{name} 中断/超时；结果未知，不重试") from exc
    except OSError as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise HandoffError(f"{name} 无法执行: {exc}") from exc
    finally:
        evidence["finished_wall_ns"] = time.time_ns()
        atomic_json(directory / f"{name}.json", evidence)
    if evidence["returncode"] != 0:
        raise HandoffError(f"{name} 失败 rc={evidence['returncode']}；后续命令未执行")
    return evidence


def handoff(root: Path, config_path: Path) -> Json:
    """一次显式交接；与 prepare 使用 .lifecycle.lock 防止并发接管。"""
    _assert_no_round(root)
    config = read_json(config_path)
    specification = config.get("handoff")
    if not isinstance(specification, dict):
        raise ValueError("必须显式提供 handoff 配置，不默认停止任何进程")
    inspect_command = argv(specification.get("inspect_command"))
    stops = specification.get("stop_commands")
    if not isinstance(stops, list):
        raise ValueError("handoff.stop_commands 必须显式配置为 argv 数组列表")
    stop_commands = [argv(command) for command in stops]
    devices = config.get("devices")
    if not isinstance(devices, list) or any(
        not isinstance(device, str) or not device.startswith("/") for device in devices
    ):
        raise ValueError("devices 必须显式配置绝对设备路径数组")
    if not devices and config.get("synthetic") is not True:
        raise ValueError("真实交接不可省略 devices 释放核对")
    timeout = config.get("timeout_s", 30.0)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout_s 必须为有限正数")
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lifecycle.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise HandoffError("另一个 prepare/交接操作正在执行；未执行交接") from exc
        _assert_no_round(root)
        identifier = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:12]
        directory = root / ("handoff-" + identifier)
        directory.mkdir()
        atomic_json(directory / "config.json", config)
        result: Json = {
            "handoff_id": identifier,
            "directory": str(directory.resolve()),
            "ok": False,
            "started_wall_ns": time.time_ns(),
            "synthetic": config.get("synthetic", False),
            "automatic_restore": False,
            "commands": [],
            "vendor_services": "not restored; operator chooses when to restore",
        }
        atomic_json(directory / "handoff.json", result)
        atomic_json(
            root / "handoff_latest.json",
            {
                "handoff_id": identifier,
                "directory": str(directory.resolve()),
                "ok": False,
                "state": "running",
            },
        )
        try:
            # 原状态的完整 stdout/stderr 先落盘，后续停止失败仍可追溯。
            _assert_no_round(root)
            result["commands"].append(
                _run(inspect_command, directory, "inspect", float(timeout))
            )
            for index, command in enumerate(stop_commands):
                _assert_no_round(root)
                result["commands"].append(
                    _run(command, directory, f"stop_{index:02d}", float(timeout))
                )
            _assert_no_round(root)
            holders = device_holders(devices)
            atomic_json(directory / "resources_after.json", holders)
            result["holders"] = holders
            if any(holders.values()):
                raise HandoffError("停止命令已返回，但设备仍有占用者；未完成交接")
            result["ok"] = True
        except (OSError, RuntimeError, ValueError) as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            raise HandoffError(f"交接失败；证据 {directory}: {exc}") from exc
        finally:
            result["finished_wall_ns"] = time.time_ns()
            atomic_json(directory / "handoff.json", result)
            atomic_json(
                root / "handoff_latest.json",
                {
                    "handoff_id": identifier,
                    "directory": str(directory.resolve()),
                    "ok": result["ok"],
                    "finished_wall_ns": result["finished_wall_ns"],
                },
            )
        return result


def main(argv_values: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv_values)
    try:
        result = handoff(args.root, args.config)
    except (OSError, ValueError, RuntimeError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
