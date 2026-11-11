"""Transport failures cannot distinguish an unsent request from executed motion."""

from unittest.mock import Mock

import pytest
from dogzilla_device_capture.cli_arguments import Arguments

from dogzilla_capture_interfaces.msg import CaptureStatus
from dogzilla_capture_interfaces.srv import SubmitMotion
from dogzilla_device_capture import cli


@pytest.mark.parametrize(
    "failure_stage", ["call_async", "response_wait", "result", "event_wait"]
)
def test_transport_exception_is_unknown_without_retry(
    monkeypatch, capsys, failure_stage: str
) -> None:
    node = Mock()
    client = Mock()
    future = Mock()
    client.wait_for_service.return_value = True
    client.call_async.return_value = future
    future.done.return_value = True
    future.result.return_value = SubmitMotion.Response(
        accepted=True, reason="accepted", request_id="transport-case"
    )
    node.create_client.return_value = client

    def subscribe(message_type, _topic, callback, _qos):
        if message_type is CaptureStatus:
            callback(
                CaptureStatus(
                    session_id="test-session", state="READY", enable_motion=True
                )
            )

    node.create_subscription.side_effect = subscribe
    if failure_stage == "call_async":
        client.call_async.side_effect = RuntimeError("middleware-failed-after-send")
    elif failure_stage == "result":
        future.result.side_effect = RuntimeError("response-decode-failed")

    wait_count = 0

    def wait(_node, condition, _deadline):
        nonlocal wait_count
        wait_count += 1
        if failure_stage == "response_wait" and wait_count == 2:
            raise RuntimeError("executor-failed-awaiting-response")
        if failure_stage == "event_wait" and wait_count == 3:
            raise RuntimeError("executor-failed-awaiting-write-event")
        return condition()

    monkeypatch.setattr(cli, "wait_until", wait)
    monkeypatch.setattr(cli.uuid, "uuid4", lambda: "transport-case")
    result = cli.run_command(node, Arguments("forward", "/capture/device", 1.0, 5, 0.2))
    assert result == 3
    assert client.call_async.call_count == 1
    client.remove_pending_request.assert_not_called()
    future.cancel.assert_not_called()
    output = capsys.readouterr()
    assert "transport-case" in output.err
    assert "未知" in output.err
    assert "不会" in output.err
    assert "未发送请求" not in output.err
    assert "Traceback" not in output.err
