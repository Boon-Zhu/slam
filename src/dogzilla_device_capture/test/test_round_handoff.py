"""交接测试仅运行临时 Python 子进程，不停止任何真实服务。"""

import fcntl
import json
import sys
from pathlib import Path

import pytest

from dogzilla_device_capture import round_handoff


def command(source):
    return [sys.executable, "-c", source]


def configuration(tmp_path, stops, timeout=3):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "synthetic": True,
                "devices": [],
                "timeout_s": timeout,
                "handoff": {
                    "inspect_command": command(
                        "print('original service snapshot'); import sys; print('inspect stderr', file=sys.stderr)"
                    ),
                    "stop_commands": stops,
                },
            }
        )
    )
    return path


def test_explicit_handoff_saves_inspection_before_stop(tmp_path):
    config = configuration(
        tmp_path,
        [
            command(
                "print('synthetic stop stdout'); import sys; print('synthetic stop stderr', file=sys.stderr)"
            )
        ],
    )
    root = tmp_path / "robot"
    result = round_handoff.handoff(root, config)
    evidence = Path(result["directory"])
    assert result["ok"] and not result["automatic_restore"]
    assert "original service snapshot" in (evidence / "inspect.stdout.log").read_text()
    assert "synthetic stop stderr" in (evidence / "stop_00.stderr.log").read_text()
    assert json.loads((root / "handoff_latest.json").read_text())["ok"]
    assert json.loads((evidence / "resources_after.json").read_text()) == {}
    assert (
        result["commands"][0]["finished_wall_ns"]
        <= result["commands"][1]["started_wall_ns"]
    )


def test_existing_round_refuses_even_inspection(tmp_path):
    root = tmp_path / "robot"
    (root / "current").mkdir(parents=True)
    (root / "current" / "round.json").write_text('{"state":"recording"}')
    marker = tmp_path / "should_not_exist"
    config = configuration(
        tmp_path, [command(f"open({str(marker)!r}, 'w').write('unexpected')")]
    )
    with pytest.raises(round_handoff.HandoffError, match="current"):
        round_handoff.handoff(root, config)
    assert not marker.exists()
    assert not list(root.glob("handoff-*"))


def test_failed_stop_keeps_logs_and_never_runs_later_command(tmp_path):
    marker = tmp_path / "should_not_exist"
    config = configuration(
        tmp_path,
        [
            command(
                "import sys; print('failure evidence'); print('failed', file=sys.stderr); sys.exit(7)"
            ),
            command(f"open({str(marker)!r}, 'w').write('unexpected')"),
        ],
    )
    root = tmp_path / "robot"
    with pytest.raises(round_handoff.HandoffError, match="rc=7"):
        round_handoff.handoff(root, config)
    evidence = next(root.glob("handoff-*"))
    assert "failure evidence" in (evidence / "stop_00.stdout.log").read_text()
    assert json.loads((evidence / "stop_00.json").read_text())["returncode"] == 7
    assert not json.loads((evidence / "handoff.json").read_text())["ok"]
    assert not marker.exists()
    assert not json.loads((root / "handoff_latest.json").read_text())["ok"]


def test_inspect_failure_never_stops(tmp_path):
    marker = tmp_path / "should_not_exist"
    config = configuration(
        tmp_path, [command(f"open({str(marker)!r}, 'w').write('unexpected')")]
    )
    value = json.loads(config.read_text())
    value["handoff"]["inspect_command"] = command("raise SystemExit(9)")
    config.write_text(json.dumps(value))
    with pytest.raises(round_handoff.HandoffError, match="inspect"):
        round_handoff.handoff(tmp_path / "robot", config)
    assert not marker.exists()


def test_resources_still_held_refuse_success(tmp_path, monkeypatch):
    config = configuration(tmp_path, [])
    monkeypatch.setattr(
        round_handoff, "device_holders", lambda _devices: {"synthetic": [123]}
    )
    root = tmp_path / "robot"
    with pytest.raises(round_handoff.HandoffError, match="占用"):
        round_handoff.handoff(root, config)
    evidence = next(root.glob("handoff-*"))
    assert json.loads((evidence / "resources_after.json").read_text()) == {
        "synthetic": [123]
    }
    assert not json.loads((root / "handoff_latest.json").read_text())["ok"]


def test_timeout_retains_output_without_retry(tmp_path):
    config = configuration(
        tmp_path,
        [command("import time; print('before timeout', flush=True); time.sleep(5)")],
        timeout=0.2,
    )
    root = tmp_path / "robot"
    with pytest.raises(round_handoff.HandoffError, match="超时"):
        round_handoff.handoff(root, config)
    evidence = next(root.glob("handoff-*"))
    assert "before timeout" in (evidence / "stop_00.stdout.log").read_text()
    assert json.loads((evidence / "stop_00.json").read_text())["timed_out"]


def test_lifecycle_lock_blocks_concurrent_prepare_handoff(tmp_path):
    root = tmp_path / "robot"
    root.mkdir()
    config = configuration(tmp_path, [])
    with (root / ".lifecycle.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(round_handoff.HandoffError, match="另一个"):
            round_handoff.handoff(root, config)
    assert not list(root.glob("handoff-*"))


def test_failed_attempt_replaces_previous_success_pointer(tmp_path):
    root = tmp_path / "robot"
    good = configuration(tmp_path, [])
    old = round_handoff.handoff(root, good)
    bad = configuration(tmp_path, [command("raise SystemExit(3)")])
    with pytest.raises(round_handoff.HandoffError):
        round_handoff.handoff(root, bad)
    latest = json.loads((root / "handoff_latest.json").read_text())
    assert latest["handoff_id"] != old["handoff_id"]
    assert not latest["ok"]
    assert Path(old["directory"]).is_dir()
