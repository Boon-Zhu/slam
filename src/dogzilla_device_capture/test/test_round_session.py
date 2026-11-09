"""不触碰时钟或设备的高影响状态边界测试。"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest
from dogzilla_device_capture.round_config import read_json, validate_config, write_json
from dogzilla_device_capture.round_preflight import check_chrony
from dogzilla_device_capture.round_session import (
    Supervisor,
    clean,
    live_process_group,
    prepare_round,
    seal_orphan,
    status,
)


def synthetic_config() -> dict:
    return json.loads(
        (Path(__file__).parents[1] / "config" / "round_synthetic.json").read_text()
    )


def make_session(tmp_path: Path) -> Supervisor:
    current = tmp_path / "current"
    current.mkdir()
    write_json(current / "config.json", synthetic_config())
    write_json(
        current / "round.json",
        {
            "round_id": "test",
            "state": "prepared",
            "mode": "stationary",
            "synthetic": True,
        },
    )
    return Supervisor(current)


def ready_probe(session: Supervisor) -> dict:
    return {
        "ok": True,
        "state": "READY",
        "current_request_id": "",
        "firmware_valid": True,
        "backend": "mock",
        "enable_motion": False,
        "session_id": "one",
        "sources": {
            source["topic"]: {"available": True} for source in session.config["sources"]
        },
    }


def test_existing_round_rejects_prepare_before_clock_or_spawn(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    with pytest.raises(RuntimeError, match="禁止校时"):
        prepare_round(tmp_path, session.current / "config.json", "stationary", True)
    assert read_json(session.current / "round.json")["state"] == "prepared"


def test_missing_source_requires_exact_explicit_acceptance(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    probe = ready_probe(session)
    probe["sources"]["/camera/image_raw"]["available"] = False
    session.probe = Mock(return_value=probe)
    session.spawn = Mock()
    with pytest.raises(RuntimeError, match="/camera/image_raw"):
        session.start([])
    session.spawn.assert_not_called()
    assert session.state["state"] == "prepared"


def test_finish_rejects_pending_motion_without_closing_bag(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    probe = ready_probe(session)
    probe["current_request_id"] = "pending"
    session.probe = Mock(return_value=probe)
    session.close_round = Mock()
    with pytest.raises(RuntimeError, match="仍有动作"):
        session.finish()
    session.close_round.assert_not_called()


def test_recorder_failure_calls_stop_even_if_disk_evidence_fails(
    tmp_path: Path,
) -> None:
    session = make_session(tmp_path)
    session.command = Mock(return_value=Mock(returncode=0))
    session.stop_child = Mock()
    session.event = Mock(side_effect=OSError("disk full"))
    session.recording_failed("write error")
    command = session.command.call_args.args[0]
    assert command[-1] == "stop"
    assert session.state["state"] == "failed"
    assert session.state["stop_result"]["physical_state"] == "not_verified"


def test_source_warning_does_not_stop_or_restart(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.state["state"] = "recording"
    session.children["recorder"] = Mock(poll=Mock(return_value=None))
    session.health = Mock(return_value={"warnings": ["/scan missing"], "fatal": None})
    session.command = Mock()
    session.monitor()
    session.command.assert_not_called()
    assert session.state["state"] == "recording"
    assert session.state["source_warnings"] == ["/scan missing"]


def test_dead_supervisor_status_is_unknown_without_repeating_action(
    tmp_path: Path,
) -> None:
    session = make_session(tmp_path)
    session.state["supervisor_pid"] = 99999999
    session.save()
    assert status(session.current)["observed_state"] == "unknown"


def test_clean_requires_verified_matching_receipt(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.state["state"] = "finished"
    session.save()
    write_json(session.current / "manifest.json", {})
    receipt = tmp_path / "receipt.json"
    write_json(receipt, {"ok": True, "round_id": "wrong", "manifest_sha256": "wrong"})
    with pytest.raises(RuntimeError, match="禁止清理"):
        clean(tmp_path, receipt)
    assert session.current.exists()


def test_synthetic_cannot_silently_be_real() -> None:
    with pytest.raises(ValueError, match="synthetic"):
        validate_config(synthetic_config(), False)


def test_clock_tracking_requires_synchronized_reference() -> None:
    evidence = check_chrony(
        "Reference ID : AABBCCDD (time.example)\nStratum : 3\nSystem time : 0.000012 seconds slow of NTP time\nLeap status : Normal\n"
    )
    assert evidence["synced"] is True
    assert evidence["offset_s"] == -0.000012
    evidence = check_chrony(
        "Reference ID : 00000000\nStratum : 0\nSystem time : 0.0 seconds slow of NTP time\nLeap status : Not synchronised\n"
    )
    assert evidence["synced"] is False


def test_orphan_sealing_rejects_remaining_process_then_preserves_evidence(
    tmp_path: Path,
) -> None:
    import os

    from dogzilla_device_capture.round_session import process_identity, seal_orphan

    session = make_session(tmp_path)
    session.state["processes"] = {
        "entry": {"pid": os.getpid(), "start_ticks": process_identity(os.getpid())}
    }
    session.save()
    with pytest.raises(RuntimeError, match="仍有本轮进程"):
        seal_orphan(tmp_path)
    session.state["processes"] = {}
    session.save()
    result = seal_orphan(tmp_path)
    assert result["round"]["state"] == "finished_with_errors"
    assert (session.current / "manifest.json").exists()


def test_firmware_or_backend_gate_cannot_be_accepted_as_missing(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    probe = ready_probe(session)
    probe["firmware_valid"] = False
    session.probe = Mock(return_value=probe)
    session.spawn = Mock()
    with pytest.raises(RuntimeError, match="有效固件"):
        session.start(["/camera/image_raw"])
    session.spawn.assert_not_called()


def test_timeout_preserves_subprocess_output(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    session = make_session(tmp_path)

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(
            ["probe"], 1, output=b"partial-out", stderr=b"partial-error"
        )

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="结果未知"):
        session.command(["probe"], "probe")
    assert (session.current / "probe.stdout.log").read_bytes() == b"partial-out"
    assert (session.current / "probe.stderr.log").read_bytes() == b"partial-error"


def test_deployment_snapshot_preserves_actual_external_configuration(
    tmp_path: Path,
) -> None:
    from dogzilla_device_capture.round_config import sha256, snapshot_deployment

    current = tmp_path / "current"
    current.mkdir()
    source = tmp_path / "camera.yaml"
    source.write_text("camera: actual-format\n")
    result = snapshot_deployment(current, {str(source): sha256(source)})
    copied = current / result[str(source)]["snapshot"]
    assert copied.read_bytes() == source.read_bytes()
    assert result[str(source)]["sha256"] == sha256(copied)


def test_clean_serializes_verification_with_prepare_and_other_clean(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from dogzilla_device_capture import archive

    session = make_session(tmp_path)
    session.state["state"] = "finished"
    session.save()
    archive.seal_round(session.current)
    exported = archive.export_round(session.current, tmp_path / "computer")
    receipt = exported / "verification" / "export_receipt.json"
    config = tmp_path / "next_config.json"
    write_json(config, synthetic_config())
    checked, resume = threading.Event(), threading.Event()
    verify = archive.verify_export

    def paused_verify(*args, **kwargs):
        result = verify(*args, **kwargs)
        checked.set()
        assert resume.wait(5)
        return result

    with monkeypatch.context() as patch:
        patch.setattr(archive, "verify_export", paused_verify)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(clean, tmp_path, receipt)
            try:
                assert checked.wait(5)
                with pytest.raises(BlockingIOError):
                    clean(tmp_path, receipt)
                with pytest.raises(BlockingIOError):
                    prepare_round(tmp_path, config, "stationary", True)
                assert session.current.exists()
            finally:
                resume.set()
            assert pending.result(timeout=5)["cleaned_round_id"] == "test"
    assert not session.current.exists()
    # A new round after the lock is released must reject the old receipt.
    new = make_session(tmp_path)
    new.state.update(round_id="new-round", state="finished")
    new.save()
    archive.seal_round(new.current)
    with pytest.raises(RuntimeError, match="禁止清理"):
        clean(tmp_path, receipt)
    assert read_json(new.current / "round.json")["round_id"] == "new-round"


@pytest.mark.parametrize("operation", ["start", "finish"])
def test_failed_probe_cannot_reuse_old_ready_evidence(
    tmp_path: Path,
    operation: str,
) -> None:
    session = make_session(tmp_path)
    old = ready_probe(session)
    write_json(session.current / f"{operation}_probe.json", old)
    session.command = Mock(side_effect=RuntimeError("new probe timeout"))
    session.spawn = Mock()
    session.close_round = Mock()
    with pytest.raises(RuntimeError, match="new probe timeout"):
        session.start([]) if operation == "start" else session.finish()
    session.spawn.assert_not_called()
    session.close_round.assert_not_called()
    assert session.state["state"] == "prepared"
    assert read_json(session.current / f"{operation}_probe.json") == old


def test_each_probe_requires_its_own_completed_report(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    outputs = []

    def command(argv, _name):
        path = Path(argv[argv.index("--output") + 1])
        outputs.append(path)
        if len(outputs) == 1:
            write_json(path, ready_probe(session))

    session.command = Mock(side_effect=command)
    assert session.probe("start_probe")["ok"]
    with pytest.raises(FileNotFoundError):
        session.probe("start_probe")
    assert outputs[0] != outputs[1]
    assert outputs[0].exists()


@pytest.mark.parametrize("leader_exits_first", [True, False])
def test_close_round_stops_descendants_before_sealing(
    tmp_path: Path,
    leader_exits_first: bool,
) -> None:
    from dogzilla_device_capture.archive import verify_export

    session = make_session(tmp_path)
    session.config["timeout_s"] = 0.2
    pid_file = session.current / "descendant.pid"
    code = """
import os, signal, sys, time
child = os.fork()
if child:
    if sys.argv[2] == 'exit':
        os._exit(0)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    while True:
        time.sleep(1)
signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)
with open(sys.argv[1], 'w') as output:
    output.write(str(os.getpid()))
while True:
    print('synthetic descendant', flush=True)
    time.sleep(0.02)
"""
    session.spawn(
        "test_driver",
        [
            sys.executable,
            "-c",
            code,
            str(pid_file),
            "exit" if leader_exits_first else "wait",
        ],
    )
    child = session.children["test_driver"]
    try:
        deadline = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert pid_file.exists()
        assert live_process_group(child.pid)
        if leader_exits_first:
            child.wait(timeout=5)
            with pytest.raises(RuntimeError, match="仍有本轮进程"):
                seal_orphan(tmp_path)
        session.close_round()
        assert not live_process_group(child.pid)
        assert child.poll() is not None
        assert session.state["state"] == "finished_with_errors"  # escalation recorded
        time.sleep(0.1)
        assert verify_export(session.current, write_report=False)["ok"]
    finally:
        if live_process_group(child.pid):
            os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=5)
        for stream in session.logs:
            stream.close()


def test_unconfirmed_group_exit_prevents_seal_but_stops_other_drivers(
    tmp_path: Path,
) -> None:
    session = make_session(tmp_path)
    session.children = {"one": Mock(), "two": Mock()}
    session.stop_child = Mock(side_effect=lambda name: name != "two")
    with pytest.raises(RuntimeError, match="拒绝封存"):
        session.close_round()
    assert {call.args[0] for call in session.stop_child.call_args_list} == {
        "recorder",
        "one",
        "two",
    }
    assert session.state["state"] == "failed"
    assert not (session.current / "manifest.json").exists()
