"""机器人本地分步采集：独立后台进程、明确状态与不可覆盖的证据。"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import importlib.metadata
import json
import math
import os
import platform
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import IO, Any

from .round_config import (
    Json,
    argv,
    read_json,
    sha256,
    snapshot_deployment,
    validate_config,
    write_json,
)

TERMINAL = {"finished", "finished_with_errors", "prepare_failed"}


def process_identity(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return ""


def live_process_group(pgid: int) -> list[int]:
    """只忽略已无文件描述符的僵尸；不能把 leader 退出视作整组退出。"""
    members = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            fields = (process / "stat").read_text().rsplit(")", 1)[1].split()
        except FileNotFoundError:
            continue
        if int(fields[2]) == pgid and fields[0] not in {"Z", "X"}:
            members.append(int(process.name))
    return members


def device_holders(devices: list[str]) -> Json:
    """按字符设备 st_rdev 检查，权限不足必须显式失败。"""
    if not devices:
        return {}
    if Path("/proc/1/comm").read_text().strip() not in {"systemd", "init"}:
        raise RuntimeError("设备所有权核对要求宿主 PID 视图（--pid host）")
    result: Json = {device: [] for device in devices}
    targets = {}
    for device in devices:
        info = os.stat(device)
        if not stat.S_ISCHR(info.st_mode):
            raise RuntimeError(f"不是字符设备: {device}")
        targets[info.st_rdev] = device
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            for descriptor in (process / "fd").iterdir():
                try:
                    item = descriptor.stat()
                except FileNotFoundError:
                    continue
                if stat.S_ISCHR(item.st_mode) and item.st_rdev in targets:
                    result[targets[item.st_rdev]].append(int(process.name))
        except FileNotFoundError:
            continue
        except PermissionError as exc:
            raise RuntimeError(
                "设备所有权不可核实：需 host PID 视图及 /proc 读取权限"
            ) from exc
    return result


class Supervisor:
    def __init__(self, current: Path) -> None:
        self.current = current
        self.config = read_json(current / "config.json")
        self.state = read_json(current / "round.json")
        self.children: dict[str, subprocess.Popen[bytes]] = {}
        self.logs: list[IO[bytes]] = []
        self.running = True
        self.interrupted = False
        self.socket_path = current.parent / "control.sock"

    def save(self) -> None:
        self.state["updated_ns"] = time.time_ns()
        write_json(self.current / "round.json", self.state)

    def event(self, kind: str, **detail: Any) -> None:
        with (self.current / "timeline.jsonl").open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "kind": kind,
                        "wall_ns": time.time_ns(),
                        "mono_ns": time.monotonic_ns(),
                        **detail,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    def command(
        self, command: list[str], name: str, *, allow_failure: bool = False
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            output = subprocess.run(
                command,
                capture_output=True,
                timeout=float(self.config["timeout_s"]) + 5,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            (self.current / f"{name}.stdout.log").write_bytes(exc.output or b"")
            (self.current / f"{name}.stderr.log").write_bytes(exc.stderr or b"")
            raise RuntimeError(
                f"{name} timeout; 输出已保存，结果未知，不自动重试"
            ) from exc
        (self.current / f"{name}.stdout.log").write_bytes(output.stdout)
        (self.current / f"{name}.stderr.log").write_bytes(output.stderr)
        if output.returncode and not allow_failure:
            raise RuntimeError(f"{name} failed rc={output.returncode}; 见日志")
        return output

    def spawn(self, name: str, command: list[str]) -> None:
        out = (self.current / f"{name}.stdout.log").open("ab")
        err = (self.current / f"{name}.stderr.log").open("ab")
        self.logs.extend([out, err])
        child = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        self.children[name] = child
        self.state.setdefault("processes", {})[name] = {
            "pid": child.pid,
            "start_ticks": process_identity(child.pid),
            "command": command,
        }
        self.save()

    def worker(self, operation: str, *extra: str) -> list[str]:
        return [
            sys.executable,
            "-m",
            "dogzilla_device_capture.recording",
            operation,
            "--config",
            str(self.current / "config.json"),
            *extra,
        ]

    def probe(self, name: str) -> Json:
        attempt = f"{name}-{uuid.uuid4().hex}"
        path = self.current / f"{attempt}.json"
        self.command(self.worker("probe", "--output", str(path)), attempt)
        return read_json(path)

    def prepare(self) -> None:
        self.event("prepare_requested")
        if self.config["synthetic"]:
            write_json(
                self.current / "clock.json",
                {"synthetic": True, "host_clock_changed": False, "synced": False},
            )
        else:
            clock = self.config["clock"]
            self.command(argv(clock["sync_command"]), "clock_sync")
            output = self.command(argv(clock["verify_command"]), "clock_verify")
            evidence = json.loads(output.stdout)
            write_json(self.current / "clock.json", evidence)
            if (
                evidence.get("synced") is not True
                or not evidence.get("source")
                or not math.isfinite(float(evidence["offset_s"]))
                or abs(float(evidence["offset_s"])) > clock["max_offset_s"]
            ):
                raise RuntimeError("自动校时结果未达到配置的准入条件")
        self.event("clock_checked")
        deployment = self.config.get("deployment", {})
        hashes = snapshot_deployment(self.current, deployment.get("expected_files", {}))
        versions: Json = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "files": hashes,
            "synthetic": self.config["synthetic"],
        }
        if not self.config["synthetic"]:
            environment = json.loads(
                self.command(
                    argv(deployment["environment_command"]), "deployment"
                ).stdout
            )
            if (
                environment.get("image") != deployment["expected_image"]
                or environment.get("ok") is not True
                or not environment.get("versions")
            ):
                raise RuntimeError("实际镜像/依赖部署证据不满足门禁")
            versions["environment"] = environment
        for package in ("dogzilla-device-capture",):
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package] = "source-tree"
        write_json(self.current / "deployment.json", versions)
        self.check_storage()
        holders = device_holders(self.config.get("devices", []))
        write_json(self.current / "resources_before.json", holders)
        if any(holders.values()):
            raise RuntimeError("设备仍被占用；请显式完成资源交接后创建下一轮")
        self.event("deployment_resources_checked")
        for driver in self.config["drivers"]:
            command = [
                part.replace("{round_dir}", str(self.current))
                .replace("{motion}", str(self.state["mode"] == "motion").lower())
                .replace("{python}", sys.executable)
                for part in argv(driver["command"])
            ]
            self.spawn(driver["name"], command)
        probe = self.probe("prepare_probe")
        self.check_entry(probe)
        self.state["sources"] = probe.get("sources", {})
        self.state["state"] = "prepared"
        self.event("prepared", probe=probe)
        self.save()

    def check_storage(self) -> None:
        free = shutil.disk_usage(self.current).free
        if free < self.config["minimum_free_bytes"]:
            raise RuntimeError("存储余量低于显式配置预算")
        path = self.current / ".write_probe"
        with path.open("wb") as stream:
            stream.write(b"capture-write-probe")
            stream.flush()
            os.fsync(stream.fileno())
        path.unlink()

    def check_entry(self, probe: Json) -> None:
        if (
            probe.get("state") != "READY"
            or probe.get("current_request_id")
            or not probe.get("firmware_valid")
            or probe.get("ok") is not True
        ):
            raise RuntimeError("入口未 READY、仍有动作或没有有效固件反馈")
        if probe.get("backend") != (
            "mock" if self.config["synthetic"] else "vendor"
        ) or probe.get("enable_motion") is not (self.state["mode"] == "motion"):
            raise RuntimeError("入口后端/运动开关与本轮不匹配")
        if self.state.get("entry_session_id") and self.state[
            "entry_session_id"
        ] != probe.get("session_id"):
            raise RuntimeError("入口会话已变化，禁止沿用旧轮次")
        self.state["entry_session_id"] = probe.get("session_id")

    def start(self, accepted: list[str]) -> None:
        if self.state["state"] != "prepared":
            raise RuntimeError("仅 prepared 可开始；回执未知请查询 status，不重发")
        self.check_storage()
        probe = self.probe("start_probe")
        self.check_entry(probe)
        missing = [
            source["topic"]
            for source in self.config["sources"]
            if not probe.get("sources", {})
            .get(source["topic"], {})
            .get("available", False)
        ]
        if set(accepted) != set(missing):
            raise RuntimeError(f"缺失来源须逐项明确接受（不能接受健康项）: {missing}")
        self.state["accepted_missing"] = missing
        self.state["start_requested_ns"] = time.time_ns()
        self.state["state"] = "starting"
        self.save()
        recording_config = dict(self.config)
        recording_config["sources"] = [
            source
            for source in self.config["sources"]
            if source["topic"] not in missing
        ]
        configured = {source["topic"] for source in self.config["sources"]}
        for discovered in probe.get("discovered_topics", []):
            if discovered["topic"] in configured or not discovered.get(
                "publisher_count"
            ):
                continue
            if len(discovered.get("types", [])) != 1:
                raise RuntimeError(
                    f"发现多类型话题，无法无歧义录制: {discovered['topic']}"
                )
            recording_config["sources"].append(
                {
                    "topic": discovered["topic"],
                    "type": discovered["type"],
                    "latched": discovered.get("latched", False),
                    "reliability": discovered.get("reliability", "best_effort"),
                    "require_message": False,
                    "stale_after_sec": self.config["timeout_s"],
                    "discovered": True,
                }
            )
        write_json(self.current / "recording_config.json", recording_config)
        self.spawn(
            "recorder",
            [
                sys.executable,
                "-m",
                "dogzilla_device_capture.recording",
                "record",
                "--config",
                str(self.current / "recording_config.json"),
                "--bag",
                str(self.current / "bag"),
                "--health",
                str(self.current / "recorder_health.json"),
            ],
        )
        deadline = time.monotonic() + self.config["timeout_s"]
        while time.monotonic() < deadline:
            self.monitor()
            if self.state["state"] == "failed":
                raise RuntimeError("录包失败；已尝试 stop，见状态与日志")
            health = self.health()
            if health.get("ready"):
                self.state["state"] = "recording"
                self.state["recording_ready_ns"] = time.time_ns()
                self.state["recording_receipt"] = health
                self.event("recording_ready", health=health)
                self.save()
                return
            time.sleep(0.1)
        self.recording_failed("录包实际订阅/收录就绪超时")
        raise RuntimeError("录包就绪超时；未发出成功回执，已尝试 stop")

    def health(self) -> Json:
        path = self.current / "recorder_health.json"
        return read_json(path) if path.exists() else {}

    def recording_failed(self, reason: str) -> None:
        self.state["state"] = "failed"
        self.state.setdefault("errors", []).append(reason)
        try:
            output = self.command(
                [
                    sys.executable,
                    "-m",
                    "dogzilla_device_capture.cli",
                    "--namespace",
                    self.config.get("namespace", "/capture/device"),
                    "stop",
                ],
                "failure_stop",
                allow_failure=True,
            )
            self.state["stop_result"] = {
                "returncode": output.returncode,
                "physical_state": "not_verified"
                if output.returncode == 0
                else "unknown",
            }
        except Exception as exc:
            self.state["stop_result"] = {"error": str(exc), "physical_state": "unknown"}
        self.stop_child("recorder")
        with contextlib.suppress(OSError):
            self.event("recording_failed", reason=reason)
            self.save()

    def monitor(self) -> None:
        if self.state["state"] not in {"recording", "starting"}:
            return
        child = self.children.get("recorder")
        try:
            health = self.health()
        except (OSError, ValueError) as exc:
            self.recording_failed(f"recorder health unreadable: {exc}")
            return
        if child is None or child.poll() is not None or health.get("fatal"):
            self.recording_failed(
                f"recorder exited/write failed: {health.get('fatal', '')}"
            )
            return
        if shutil.disk_usage(self.current).free == 0:
            self.recording_failed("storage full")
            return
        warnings = health.get("warnings", [])
        if warnings != self.state.get("source_warnings", []):
            self.event("source_warnings", warnings=warnings)
            self.state["source_warnings"] = warnings
            self.save()

    def _wait_process_group(
        self, child: subprocess.Popen[bytes], timeout: float
    ) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            exited = child.poll() is not None
            if not live_process_group(child.pid) and exited:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

    def stop_child(self, name: str) -> bool:
        child = self.children.get(name)
        if child is None:
            return True
        try:
            stopped = self._wait_process_group(child, 0)
            for stop_signal, timeout in (
                (signal.SIGINT, float(self.config["timeout_s"])),
                (signal.SIGTERM, 3.0),
                (signal.SIGKILL, 3.0),
            ):
                if stopped:
                    break
                if stop_signal != signal.SIGINT:
                    self.state.setdefault("errors", []).append(
                        f"{name} process group shutdown timeout; {stop_signal.name}"
                    )
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(child.pid, stop_signal)
                stopped = self._wait_process_group(child, timeout)
        except OSError as exc:
            self.state.setdefault("errors", []).append(f"{name} shutdown: {exc}")
            stopped = False
        if not stopped:
            self.state.setdefault("errors", []).append(
                f"{name} process group release unconfirmed; cannot seal"
            )
        self.state.setdefault("exit_codes", {})[name] = child.returncode
        if child.returncode != 0:
            self.state.setdefault("errors", []).append(
                f"{name} exit={child.returncode}"
            )
        return stopped

    def finish(self) -> None:
        if self.state["state"] not in {"prepared", "recording", "failed"}:
            raise RuntimeError("本轮不能正常结束")
        probe = self.probe("finish_probe")
        self.check_entry(probe)
        self.state["state"] = "finishing"
        self.save()
        self.close_round()

    def abort(self) -> None:
        self.recording_failed("操作者显式异常结束；不宣称正常完成/实际停稳")
        self.close_round()

    def close_round(self) -> None:
        from .archive import inspect_bag, seal_round

        stopped = self.stop_child("recorder")
        if (self.current / "bag").exists():
            try:
                expected = [
                    source["topic"]
                    for source in self.config["sources"]
                    if source["topic"] not in self.state.get("accepted_missing", [])
                    and source.get("require_message", True)
                ]
                report = inspect_bag(self.current / "bag", expected)
                write_json(self.current / "bag_check.json", report)
                if not report.get("ok"):
                    self.state.setdefault("errors", []).append("bag 文件/覆盖检查失败")
            except Exception as exc:
                self.state.setdefault("errors", []).append(f"bag 检查错误: {exc}")
        for name in reversed(list(self.children)):
            if name != "recorder":
                stopped = self.stop_child(name) and stopped
        if not stopped:
            self.state["state"] = "failed"
            self.save()
            raise RuntimeError("进程组释放未核实，保留原件，拒绝封存")
        for stream in self.logs:
            stream.close()
        try:
            holders = device_holders(self.config.get("devices", []))
            write_json(self.current / "resources_after.json", holders)
            if any(holders.values()):
                self.state.setdefault("errors", []).append("资源释放未核实通过")
        except Exception as exc:
            self.state.setdefault("errors", []).append(str(exc))
        self.state["state"] = (
            "finished_with_errors" if self.state.get("errors") else "finished"
        )
        self.state["closed_ns"] = time.time_ns()
        self.state["vendor_services_restored"] = False
        self.event("closed", errors=self.state.get("errors", []))
        self.save()
        seal_round(self.current)
        self.running = False

    def run(self) -> None:
        def interrupted(_number: int, _frame: object) -> None:
            self.interrupted = True

        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        self.state["supervisor_pid"] = os.getpid()
        self.state["supervisor_start_ticks"] = process_identity(os.getpid())
        self.save()
        with (self.current.parent / ".supervisor.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.socket_path.unlink(missing_ok=True)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(self.socket_path))
                os.chmod(self.socket_path, 0o600)
                server.listen(4)
                server.settimeout(0.3)
                try:
                    self.prepare()
                except Exception as exc:
                    self.state.setdefault("errors", []).append(f"prepare: {exc}")
                    self.close_round()
                while self.running:
                    if self.interrupted:
                        self.abort()
                        break
                    try:
                        self.monitor()
                    except OSError as exc:
                        self.recording_failed(
                            f"supervisor evidence write failed: {exc}"
                        )
                    try:
                        connection, _ = server.accept()
                    except TimeoutError:
                        continue
                    with connection:
                        connection.settimeout(2)
                        try:
                            request = json.loads(
                                connection.makefile("rb").readline(65536)
                            )
                            if request["operation"] == "start":
                                self.start(request.get("accept_missing", []))
                            elif request["operation"] == "finish":
                                self.finish()
                            elif request["operation"] == "abort":
                                self.abort()
                            else:
                                raise ValueError("未知操作")
                            response = {"ok": True, "round": self.state}
                        except Exception as exc:
                            response = {
                                "ok": False,
                                "error": str(exc),
                                "round": self.state,
                            }
                        try:
                            connection.sendall(json.dumps(response).encode() + b"\n")
                        except (BrokenPipeError, ConnectionResetError):
                            pass  # SSH 断开不取消已接收的操作，也不重复执行。
            self.socket_path.unlink(missing_ok=True)


def status(current: Path) -> Json:
    state = read_json(current / "round.json")
    if state["state"] not in TERMINAL:
        pid = state.get("supervisor_pid", 0)
        if not pid or process_identity(pid) != state.get("supervisor_start_ticks"):
            return {
                **state,
                "observed_state": "unknown",
                "guidance": "后台不可确认；保留文件并人工核对进程/设备，不重发动作或prepare",
            }
    health_path = current / "recorder_health.json"
    if health_path.exists():
        state["recorder_health"] = read_json(health_path)
    return {**state, "observed_state": state["state"]}


def prepare_round(root: Path, config_path: Path, mode: str, synthetic: bool) -> Json:
    config = read_json(config_path)
    config["backend"] = "mock" if synthetic else "vendor"
    config["enable_motion"] = mode == "motion"
    validate_config(config, synthetic)
    root.mkdir(parents=True, exist_ok=True)
    current = root / "current"
    with (root / ".lifecycle.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if current.exists():
            raise RuntimeError(
                "current 已存在；禁止校时、重启或覆盖，先 status/导出/显式 clean"
            )
        latest = root / "handoff_latest.json"
        if latest.exists() and not config.get("handoff_evidence"):
            handoff = read_json(latest)
            if handoff.get("ok") is not True:
                raise RuntimeError("最近资源交接失败；拒绝沿用旧成功记录")
            config["handoff_evidence"] = handoff["directory"]
        current.mkdir()
    write_json(current / "config.json", config)
    write_json(
        current / "round.json",
        {
            "round_id": time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:12],
            "state": "preparing",
            "mode": mode,
            "synthetic": synthetic,
            "created_ns": time.time_ns(),
            "errors": [],
        },
    )
    handoff_evidence = config.get("handoff_evidence")
    if handoff_evidence:
        shutil.copytree(Path(handoff_evidence), current / "handoff")
    # 将实际运行的自研模块、接口和参数一同交付；不复制/修改上游。
    shutil.copytree(
        Path(__file__).parent,
        current / "capture_source",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    from ament_index_python.packages import get_package_share_directory  # type: ignore[import-untyped]

    for package in ("dogzilla_capture_interfaces", "dogzilla_device_capture"):
        shutil.copytree(
            get_package_share_directory(package), current / "packages" / package
        )
    (current / "DATASET.md").write_text(
        "# 采集轮次\n\n本轮身份和模式见 round.json，配置见 config.json，来源/缺失及故障见各 probe、recorder_health、timeline 和日志。SYNTHETIC=true 时全部为软件测试，不是真机数据。消息定义、package.xml及CMakeLists见 packages/dogzilla_capture_interfaces（用colcon build --base-paths该目录构建并source）。完整使用指南见 packages/dogzilla_device_capture/docs，代码见 capture_source。电脑用 capture-round-archive verify/replay 核对副本；命令/写入事件不证明实际运动或停稳。外部视频按 round_id 关联，事后注明人工搬动的不连续片段；未知对应关系保留未知。\n"
    )
    # supervisor 及各工作器完整日志随轮次保存，封存后不再写入。
    with (current / "supervisor.log").open("ab") as log:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "dogzilla_device_capture.round_session",
                "--root",
                str(root),
                "_supervise",
            ],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    deadline = time.monotonic() + config["timeout_s"] * (len(config["drivers"]) + 5)
    while time.monotonic() < deadline:
        state = status(current)
        if state["state"] != "preparing":
            return state
        time.sleep(0.2)
    return {**status(current), "request_outcome": "unknown; query status, do not retry"}


def request(root: Path, operation: str, accepted: list[str]) -> Json:
    current = root / "current"
    state = status(current)
    if state["observed_state"] == "unknown":
        raise RuntimeError("后台状态未知；拒绝发送动作")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(float(read_json(current / "config.json")["timeout_s"]) * 8)
        client.connect(str(root / "control.sock"))
        client.sendall(
            json.dumps({"operation": operation, "accept_missing": accepted}).encode()
            + b"\n"
        )
        try:
            response = json.loads(client.makefile("rb").readline())
        except (TimeoutError, ValueError, ConnectionError) as exc:
            raise RuntimeError("操作结果未知；重连后 status，禁止自动重试") from exc
    return dict(response)


def clean(root: Path, receipt_path: Path) -> Json:
    from .archive import verify_export

    with (root / ".lifecycle.lock").open("a") as lifecycle:
        fcntl.flock(lifecycle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (root / ".supervisor.lock").open("a") as supervisor:
            fcntl.flock(supervisor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            current = root / "current"
            state = status(current)
            if state["state"] not in TERMINAL:
                raise RuntimeError("仅封存且已导出校验的轮次可清理")
            receipt = read_json(receipt_path)
            expected = sha256(current / "manifest.json")
            if (
                receipt.get("ok") is not True
                or receipt.get("exported") is not True
                or receipt.get("verified_directory") == str(current.resolve())
                or receipt.get("round_id") != state["round_id"]
                or receipt.get("manifest_sha256") != expected
            ):
                raise RuntimeError("导出回执与本轮不匹配，禁止清理")
            if not verify_export(current, write_report=False).get("ok"):
                raise RuntimeError("原件封存后变化，禁止清理")
            write_json(
                root / "last_clean.json",
                {
                    "round_id": state["round_id"],
                    "receipt": receipt,
                    "cleaned_ns": time.time_ns(),
                },
            )
            shutil.rmtree(current)
    return {"ok": True, "cleaned_round_id": state["round_id"]}


def seal_orphan(root: Path) -> Json:
    """后台失效后仅封存已释放的异常轮次，不杀进程、不续录、不猜测停稳。"""
    from .archive import inspect_bag, seal_round

    with (root / ".lifecycle.lock").open("a") as lifecycle:
        fcntl.flock(lifecycle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (root / ".supervisor.lock").open("a") as supervisor:
            fcntl.flock(supervisor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            current = root / "current"
            state = status(current)
            incomplete = (
                state["state"] in TERMINAL and not (current / "manifest.json").exists()
            )
            if state["observed_state"] != "unknown" and not incomplete:
                raise RuntimeError(
                    "仅后台未知或最终封存失败的轮次可 seal-orphan；正常轮次使用 finish"
                )
            if process_identity(state.get("supervisor_pid", 0)) and process_identity(
                state.get("supervisor_pid", 0)
            ) == state.get("supervisor_start_ticks"):
                raise RuntimeError("supervisor 仍存活，拒绝并发封存")
            for process in state.get("processes", {}).values():
                if process_identity(process["pid"]) == process[
                    "start_ticks"
                ] or live_process_group(process["pid"]):
                    raise RuntimeError(
                        "仍有本轮进程；先人工核对并结束，不能封存活跃数据"
                    )
            config = read_json(current / "config.json")
            holders = device_holders(config.get("devices", []))
            if any(holders.values()):
                raise RuntimeError("设备仍被占用，不能确认资源释放")
            state.pop("recorder_health", None)
            state.pop("observed_state", None)
            state["state"] = "finished_with_errors"
            state.setdefault("errors", []).append(
                "后台失效，人工释放后显式封存；物理状态未知，连续性中断"
            )
            state["closed_ns"] = time.time_ns()
            write_json(current / "round.json", state)
            write_json(current / "resources_after.json", holders)
            if (current / "bag").exists():
                write_json(current / "bag_check.json", inspect_bag(current / "bag", []))
            seal_round(current)
    return {"ok": True, "round": state}


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="机器人本地分步采集；prepare/start 不发送运动"
    )
    parser.add_argument(
        "--root", type=Path, required=True, help="宿主持久挂载的固定采集根目录"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--config", type=Path, required=True)
    prepare.add_argument(
        "--mode", choices=["stationary", "motion"], default="stationary"
    )
    prepare.add_argument("--synthetic", action="store_true")
    start = sub.add_parser("start")
    start.add_argument("--accept-missing", action="append", default=[])
    sub.add_parser("status", aliases=["stat"])
    sub.add_parser("finish")
    sub.add_parser("abort")
    sub.add_parser("seal-orphan")
    cleanup = sub.add_parser("clean")
    cleanup.add_argument("--receipt", type=Path, required=True)
    sub.add_parser("_supervise")
    options = parser.parse_args(args)
    root = options.root.resolve()
    try:
        if options.command == "_supervise":
            Supervisor(root / "current").run()
            return
        if options.command == "prepare":
            result = prepare_round(
                root, options.config, options.mode, options.synthetic
            )
        elif options.command in {"status", "stat"}:
            result = status(root / "current")
        elif options.command == "seal-orphan":
            result = seal_orphan(root)
        elif options.command == "clean":
            result = clean(root, options.receipt)
        else:
            result = request(
                root, options.command, getattr(options, "accept_missing", [])
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("ok") is False or result.get("state") == "finished_with_errors":
            raise SystemExit(2)
    except (OSError, ValueError, RuntimeError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
