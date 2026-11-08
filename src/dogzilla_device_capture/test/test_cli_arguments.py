import pytest
from dogzilla_device_capture.cli_arguments import parse_arguments


def test_explicit_motion_arguments() -> None:
    result = parse_arguments(["forward", "--input", "5", "--duration", "0.6"])
    assert result.magnitude == 5
    assert result.duration_s == 0.6
    assert result.namespace == "/capture/device"


@pytest.mark.parametrize(
    "argv",
    [
        ["forward"],
        ["forward", "--input", "21", "--duration", "1"],
        ["left", "--input", "29", "--duration", "1"],
        ["right", "--input", "71", "--duration", "1"],
        ["forward", "--input", "2", "--duration", "nan"],
        ["forward", "--input", "2", "--duration", "inf"],
        ["forward", "--input", "2", "--duration", "0"],
        ["--namespace", "relative", "status"],
    ],
)
def test_reject_invalid_commands(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_arguments(argv)


def test_stop_needs_no_motion_parameters() -> None:
    result = parse_arguments(["stop"])
    assert result.magnitude is None and result.duration_s is None
