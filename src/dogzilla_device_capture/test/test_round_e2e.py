"""真实 Humble DDS/sqlite/回放，唯一合成数据轮次；绝不访问硬件。"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from dogzilla_device_capture.archive import export_round, replay_export, verify_export
from dogzilla_device_capture.round_config import read_json, write_json


def run_round(root: Path, *args: str, success: bool = True) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dogzilla_device_capture.round_session",
            "--root",
            str(root),
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=150,
    )
    with (root.parent / "commands.jsonl").open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "args": list(args),
                    "code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            + "\n"
        )
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout + result.stderr
    return json.loads(result.stdout or result.stderr)


def scenario(tmp_path: Path, name: str) -> tuple[Path, Path]:
    target = os.environ.get("CAPTURE_ROUND_ARTIFACT_ROOT")
    directory = (
        Path(target) / (name + "-" + uuid.uuid4().hex[:8]) if target else tmp_path
    )
    directory.mkdir(parents=True, exist_ok=True)
    config = json.loads(
        (Path(__file__).parents[1] / "config" / "round_synthetic.json").read_text()
    )
    config_path = directory / "config.json"
    write_json(config_path, config)
    return directory / "robot", config_path


def emergency_cleanup(root: Path) -> None:
    """仅清理本测试创建且身份仍一致的进程，不删除任何产物。"""
    from dogzilla_device_capture.round_session import process_identity

    if not (root / "current" / "round.json").exists():
        return
    state = read_json(root / "current" / "round.json")
    if state["state"] in {"finished", "finished_with_errors"}:
        return
    try:
        run_round(root, "abort")
    except Exception:
        for info in state.get("processes", {}).values():
            if process_identity(info["pid"]) == info["start_ticks"]:
                os.killpg(info["pid"], signal.SIGTERM)
        if process_identity(state.get("supervisor_pid", 0)) == state.get(
            "supervisor_start_ticks"
        ):
            os.kill(state["supervisor_pid"], signal.SIGTERM)


def test_round_prepare_record_export_replay_clean(tmp_path: Path) -> None:
    root, config = scenario(tmp_path, "normal")
    try:
        prepared = run_round(root, "prepare", "--config", str(config), "--synthetic")
        assert prepared["state"] == "prepared"
        assert prepared["mode"] == "stationary"
        assert prepared["synthetic"] is True
        receipt = run_round(root, "start")
        assert receipt["round"]["state"] == "recording"
        # 前一个 CLI 已退出，新的 CLI 可重连查询后台，且重复prepare无校时/覆盖。
        assert run_round(root, "status")["observed_state"] == "recording"
        run_round(
            root, "prepare", "--config", str(config), "--synthetic", success=False
        )
        time.sleep(0.8)
        finished = run_round(root, "finish")
        assert finished["round"]["state"] == "finished", finished
        exported = export_round(root / "current", root.parent / "computer")
        assert verify_export(exported)["ok"]
        replay = replay_export(exported, timeout_s=45)
        assert replay["ok"], replay
        export_receipt = exported / "verification" / "export_receipt.json"
        run_round(root, "clean", "--receipt", str(export_receipt))
        assert not (root / "current").exists()
        assert (exported / "bag" / "metadata.yaml").exists()
        write_json(
            root.parent / "e2e_result.json",
            {
                "ok": True,
                "synthetic": True,
                "exported": str(exported),
                "round_id": prepared["round_id"],
                "replay": replay,
            },
        )
    finally:
        emergency_cleanup(root)


def test_missing_source_and_recorder_exit_preserve_failed_round(tmp_path: Path) -> None:
    root, config_path = scenario(tmp_path, "failure")
    config = read_json(config_path)
    config["timeout_s"] = 5
    config["drivers"][1]["command"].append("--omit-image")
    write_json(config_path, config)
    try:
        assert (
            run_round(
                root,
                "prepare",
                "--config",
                str(config_path),
                "--synthetic",
                "--mode",
                "motion",
            )["state"]
            == "prepared"
        )
        rejected = run_round(root, "start", success=False)
        assert "/camera/image_raw" in rejected["error"]
        started = run_round(root, "start", "--accept-missing", "/camera/image_raw")
        assert started["round"]["accepted_missing"] == ["/camera/image_raw"]
        action = subprocess.run(
            [
                sys.executable,
                "-m",
                "dogzilla_device_capture.cli",
                "forward",
                "--input",
                "5",
                "--duration",
                "20",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        (root.parent / "synthetic_motion.log").write_text(action.stdout + action.stderr)
        assert action.returncode == 0
        assert run_round(root, "finish", success=False)["ok"] is False
        recorder_pid = started["round"]["processes"]["recorder"]["pid"]
        os.kill(recorder_pid, signal.SIGKILL)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = run_round(root, "status")
            if state["state"] == "failed":
                break
            time.sleep(0.2)
        assert state["state"] == "failed", state
        assert state["stop_result"]["returncode"] == 0, state
        run_round(root, "start", success=False)
        finished = run_round(root, "finish")
        assert finished["round"]["state"] == "finished_with_errors"
        exported = export_round(root / "current", root.parent / "computer")
        assert verify_export(exported)["ok"]
        assert (exported / "failure_stop.stdout.log").exists()
        assert (root / "current").exists()  # 异常证据不自动清理。
        write_json(
            root.parent / "e2e_result.json",
            {
                "ok": True,
                "synthetic": True,
                "scenario": "missing_source_and_recorder_failure",
                "round_id": started["round"]["round_id"],
                "exported": str(exported),
                "stop_result": state["stop_result"],
                "accepted_missing": started["round"]["accepted_missing"],
                "final_state": finished["round"]["state"],
                "robot_original_preserved": True,
            },
        )
    finally:
        emergency_cleanup(root)
