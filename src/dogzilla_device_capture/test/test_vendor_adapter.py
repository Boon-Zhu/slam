"""Protocol and interruption checks using captured frames and a fake UART."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
import select
import sys
import threading
import time
import types
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from dogzilla_device_capture.contracts import DeviceError
from dogzilla_device_capture.vendor_adapter import (
    QUERY_ADDRESSES,
    VENDOR_SOURCE_SHA256,
    SerialPort,
    SerialTrace,
    VendorAdapter,
    VendorFactory,
    load_pending,
    save_pending,
    validate_response,
)

from dogzilla_device_capture import vendor_adapter as implementation

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/feedback_frames.json").read_text()
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000_000_000
        self.wall = 50_000_000_000

    def monotonic_ns(self) -> int:
        return self.now

    def time_ns(self) -> int:
        return self.wall

    def sleep(self, seconds: float) -> None:
        self.now += int(seconds * 1e9)
        # Wall clock moving backwards must not extend the query deadline.
        self.wall -= 5_000_000_000


class FakeSerial:
    def __init__(self) -> None:
        self.timeout: float | None = None
        self.write_timeout: float | None = None
        self.buffer = bytearray()
        self.responses: dict[int, bytes] = {
            QUERY_ADDRESSES[name][0]: bytes.fromhex(row["frame_hex"])
            for name, row in FIXTURES.items()
        }
        self.delayed = b""
        self.writes: list[bytes] = []
        self.short_write = False
        self.fail_write = False
        self.closed = False
        self.max_read = 100
        self.on_read: Callable[[], None] = lambda: None

    def write(self, data: bytes) -> int:
        if self.fail_write:
            raise OSError("unplugged")
        self.writes.append(data)
        if self.short_write:
            return 3
        if data[3] == 2:
            self.delayed = self.responses.get(data[4], b"")
        return len(data)

    def inWaiting(self) -> int:
        if self.delayed:
            self.buffer.extend(self.delayed)
            self.delayed = b""
        return len(self.buffer)

    def read(self, size: int = 1) -> bytes:
        size = min(size, self.max_read)
        data = bytes(self.buffer[:size])
        del self.buffer[:size]
        self.on_read()
        return data

    def read_all(self) -> bytes:
        data = bytes(self.buffer)
        self.buffer.clear()
        return data

    def close(self) -> None:
        self.closed = True

    def fileno(self) -> int:
        raise RuntimeError("fake UART has no descriptor")


def request(address: int, size: int = 1) -> bytes:
    return bytes(
        [0x55, 0, 9, 2, address, size, 255 - (9 + 2 + address + size) % 256, 0, 0xAA]
    )


class FakeVendor:
    """A behavioral test double, not a bundled replacement for DOGZILLALib."""

    def __init__(self, serial: FakeSerial) -> None:
        self.ser: SerialPort = serial
        self.rx_FLAG = self.rx_COUNT = self.rx_ADDR = self.rx_LEN = 0
        self.rx_data = bytearray(50)

    def _query(self, method: str) -> object:
        address, sizes = QUERY_ADDRESSES[method]
        assert isinstance(self.ser, SerialTrace)
        self.ser.flushInput()
        self.ser.write(request(address, sizes[0]))
        self.ser.read_all()
        buffer = bytearray()
        while True:
            count = self.ser.inWaiting()
            if count:
                buffer.extend(self.ser.read(count))
                self.rx_FLAG = 5
                if len(buffer) >= 3 and len(buffer) >= buffer[2]:
                    return FIXTURES[method]["vendor_value"]

    def read_battery(self) -> object:
        return self._query("read_battery")

    def read_version(self) -> object:
        return self._query("read_version")

    def read_motor(self) -> object:
        return self._query("read_motor")

    def read_roll(self) -> object:
        return self._query("read_roll")

    def read_pitch(self) -> object:
        return self._query("read_pitch")

    def read_yaw(self) -> object:
        return self._query("read_yaw")

    def read_imu_raw(self) -> object:
        return self._query("read_imu_raw")

    def move_x(self, value: int) -> None:
        self.ser.write(bytes([0x55, 0, 9, 1, 0x30, value & 255, 0, 0, 0xAA]))

    def turn(self, value: int) -> None:
        self.ser.write(bytes([0x55, 0, 9, 1, 0x32, value & 255, 0, 0, 0xAA]))

    def stop(self) -> None:
        for address in [0x30, 0x31, 0x3C, 0x32]:
            self.ser.write(bytes([0x55, 0, 9, 1, address, 0, 0, 0, 0xAA]))


def device() -> tuple[VendorAdapter, FakeSerial, FakeVendor, FakeClock]:
    port = FakeSerial()
    vendor = FakeVendor(port)
    clock = FakeClock()
    adapter = VendorAdapter(
        vendor,
        monotonic_ns=clock.monotonic_ns,
        wall_ns=clock.time_ns,
        sleep=clock.sleep,
    )
    return adapter, port, vendor, clock


@pytest.mark.parametrize("method", list(QUERY_ADDRESSES))
def test_captured_frames_are_valid_and_preserved(method: str) -> None:
    adapter, port, vendor, _ = device()
    port.max_read = 4
    sample = adapter.query(method, lambda: False)
    assert sample.valid, sample.error
    raw = b"".join(chunk.data for chunk in sample.chunks if chunk.op == "read")
    assert raw.hex() == FIXTURES[method]["frame_hex"]
    assert vendor.rx_FLAG == 0
    assert port.timeout == 0.005 and port.write_timeout == 0.05
    if method == "read_motor":
        assert raw[-6:-3] == b"\x00\xff\x00"
        assert len(sample.values) == 12
    if method == "read_version":
        assert raw[5:-3] == b"M-4.0.1-Y\0"
        assert sample.text == "4.0.1-Y"


def test_timeout_uses_monotonic_time_despite_wall_jump() -> None:
    adapter, port, _, clock = device()
    port.responses.clear()
    start = clock.now
    sample = adapter.query("read_imu_raw", lambda: False)
    assert not sample.valid and sample.error == "timeout"
    assert sample.mono_end_ns - start == 1_000_000_000
    assert sample.wall_end_ns < sample.wall_start_ns


def test_interrupt_prevents_next_read_and_stop_can_write() -> None:
    adapter, port, _, _ = device()
    port.responses.clear()
    sample = adapter.query("read_imu_raw", lambda: bool(port.writes))
    assert sample.error == "interrupted"
    chunks = adapter.stop()
    assert [c.data[4] for c in chunks if c.op == "write"] == [0x30, 0x31, 0x3C, 0x32]


def test_partial_response_late_same_address_not_misassociated() -> None:
    adapter, port, _, _ = device()
    full = port.responses[0x65]
    port.responses[0x65] = full[:12]
    sample = adapter.query(
        "read_imu_raw",
        lambda: not port.buffer and len(port.writes) == 1 and not port.delayed,
    )
    assert sample.error == "interrupted"
    count = len(port.writes)
    pending = adapter.query("read_imu_raw", lambda: False)
    assert pending.error == "attribution_uncertain_pending_response"
    assert len(port.writes) == count
    port.buffer.extend(full[12:])
    late = adapter.query("read_imu_raw", lambda: False)
    assert late.error == "late_response_consumed" and not late.valid
    assert len(port.writes) == count
    assert b"".join(c.data for c in late.chunks if c.op == "late_read") == full[12:]
    port.responses[0x65] = full
    fresh = adapter.query("read_imu_raw", lambda: False)
    assert fresh.valid


def test_late_reply_in_different_query_is_not_valid_current_reply() -> None:
    adapter, port, _, _ = device()
    old = port.responses.pop(0x65)
    assert adapter.query("read_imu_raw", lambda: False).error == "timeout"
    port.buffer.extend(old)
    sample = adapter.query("read_battery", lambda: False)
    assert sample.valid
    assert any(c.op == "flush_input_discard" and c.data == old for c in sample.chunks)
    port.responses[0x65] = old
    assert adapter.query("read_imu_raw", lambda: False).valid


def test_pre_request_discard_cannot_discharge_new_unanswered_request() -> None:
    adapter, port, _, _ = device()
    port.buffer.extend(port.responses.pop(1))
    sample = adapter.query("read_battery", lambda: False)
    assert sample.error == "timeout"
    assert (
        adapter.query("read_battery", lambda: False).error
        == "attribution_uncertain_pending_response"
    )


@pytest.mark.parametrize(
    "offset,value,reason",
    [(3, 0x13, "response_type"), (4, 0x02, "response_address"), (-3, 0, "checksum")],
)
def test_protocol_rejects_wrong_type_address_checksum(
    offset: int, value: int, reason: str
) -> None:
    adapter, port, _, _ = device()
    data = bytearray(port.responses[1])
    data[offset] = value
    port.responses[1] = bytes(data)
    sample = adapter.query("read_battery", lambda: False)
    assert not sample.valid and sample.error == reason


def test_short_write_retains_attempt_and_actual_count() -> None:
    adapter, port, _, _ = device()
    port.short_write = True
    with pytest.raises(DeviceError) as exc:
        adapter.move("forward", 5)
    assert [c.op for c in exc.value.chunks] == ["write_request", "write"]
    assert len(exc.value.chunks[-1].data) == 3


def test_serial_failure_is_distinct_from_bad_feedback() -> None:
    adapter, port, _, _ = device()
    port.fail_write = True
    sample = adapter.query("read_battery", lambda: False)
    assert sample.error.startswith("serial_error:")
    assert any(c.op == "write_failed_unknown_count" for c in sample.chunks)


def test_unknown_write_count_keeps_pending_across_close(tmp_path: Path) -> None:
    class AcceptedThenFailed(FakeSerial):
        def write(self, data: bytes) -> int:
            super().write(data)
            raise OSError("driver reported failure after device accepted request")

    port = AcceptedThenFailed()
    marker = tmp_path / "session"
    adapter = VendorAdapter(FakeVendor(port), recovery_marker=marker)
    sample = adapter.query("read_imu_raw", lambda: False)
    assert sample.error.startswith("serial_error:")
    assert port.delayed == bytes.fromhex(FIXTURES["read_imu_raw"]["frame_hex"])
    adapter.close()
    assert load_pending(marker)[0] == {0x65}


def test_close_is_idempotent_and_does_not_send_stop() -> None:
    adapter, port, _, _ = device()
    adapter.close()
    adapter.close()
    assert port.closed and port.writes == []
    with pytest.raises(DeviceError, match="device_closed"):
        adapter.query("read_battery", lambda: False)


def test_second_thread_cannot_use_uart() -> None:
    adapter, port, _, _ = device()
    errors: list[Exception] = []

    def other_thread() -> None:
        try:
            adapter.stop()
        except DeviceError as exc:
            errors.append(exc)

    thread = threading.Thread(target=other_thread)
    thread.start()
    thread.join()
    assert errors and isinstance(errors[0], DeviceError)
    assert port.writes == []


def test_pending_state_survives_orderly_reopen(tmp_path: Path) -> None:
    marker = tmp_path / "session"
    adapter, port, vendor, clock = device()
    adapter = VendorAdapter(
        vendor,
        monotonic_ns=clock.monotonic_ns,
        wall_ns=clock.time_ns,
        sleep=clock.sleep,
        recovery_marker=marker,
    )
    port.responses.clear()
    assert adapter.query("read_battery", lambda: False).error == "timeout"
    adapter.close()
    pending, partial = load_pending(marker)
    assert pending == {1} and partial == b""
    save_pending(marker, {1, 0x65}, b"\x55\x00")
    assert load_pending(marker) == ({1, 0x65}, b"\x55\x00")


def test_corrupt_recovery_metadata_does_not_grant_freshness(tmp_path: Path) -> None:
    marker = tmp_path / "session"
    marker.write_text("unfinished")
    pending, _ = load_pending(marker)
    assert pending == {entry[0] for entry in QUERY_ADDRESSES.values()}


def test_recovered_pending_source_does_not_block_other_sources(tmp_path: Path) -> None:
    port = FakeSerial()
    vendor = FakeVendor(port)
    clock = FakeClock()
    marker = tmp_path / "session"
    adapter = VendorAdapter(
        vendor,
        pending_addresses={0x65},
        recovery_marker=marker,
        monotonic_ns=clock.monotonic_ns,
        wall_ns=clock.time_ns,
        sleep=clock.sleep,
    )
    assert (
        adapter.query("read_imu_raw", lambda: False).error
        == "attribution_uncertain_pending_response"
    )
    assert not port.writes
    assert adapter.query("read_battery", lambda: False).valid
    assert adapter.move("forward", 1)
    adapter.close()
    assert load_pending(marker)[0] == {0x65}


def test_host_device_holder_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    master, slave = os.openpty()
    proc = tmp_path / "proc"
    (proc / "1").mkdir(parents=True)
    (proc / "1" / "comm").write_text("systemd\n")
    other = proc / "999999" / "fd"
    other.mkdir(parents=True)
    (other / "7").symlink_to(os.ttyname(slave))
    original_path = Path
    original_stat = Path.stat

    def alias_permissions(path: Path, *args: object, **kwargs: object) -> object:
        result = original_stat(path, *args, **kwargs)
        if path == other / "7":
            return types.SimpleNamespace(
                st_mode=result.st_mode ^ 0o077, st_rdev=result.st_rdev
            )
        return result

    monkeypatch.setattr(Path, "stat", alias_permissions)

    def redirected_path(value: str) -> Path:
        if value == "/proc" or value.startswith("/proc/"):
            return proc / value.removeprefix("/proc").lstrip("/")
        return original_path(value)

    monkeypatch.setattr(implementation, "Path", redirected_path)
    try:
        with pytest.raises(DeviceError, match="serial_already_owned:pid=999999"):
            implementation.check_device_holders(os.ttyname(slave))
        (other / "7").unlink()
        implementation.check_device_holders(os.ttyname(slave))
    finally:
        os.close(slave)
        os.close(master)


def test_non_character_device_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "not-a-uart"
    target.touch()
    original = Path.read_text

    def read_text(path: Path, *args: object, **kwargs: object) -> str:
        if str(path) == "/proc/1/comm":
            return "systemd\n"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(DeviceError, match="not_character_device"):
        implementation.check_device_holders(str(target))


def test_factory_lock_hash_and_pending_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = FakeSerial()
    vendor = FakeVendor(port)
    source = "test-only factory source"
    module = types.ModuleType("fake_vendor")
    module.__file__ = "/test-only/vendor.py"

    def factory(*, port: str, baud: int, verbose: bool) -> FakeVendor:
        assert port == "/test/uart" and baud == 115200 and verbose is False
        return vendor

    module.DOGZILLA = factory
    monkeypatch.setattr(implementation.importlib, "import_module", lambda _: module)
    monkeypatch.setattr(implementation.inspect, "getmodule", lambda _: module)
    monkeypatch.setattr(implementation.inspect, "getsource", lambda _: source)
    monkeypatch.setattr(implementation, "check_device_holders", lambda _: None)
    monkeypatch.setattr(FakeSerial, "fileno", lambda _: 123)
    monkeypatch.setattr(implementation.fcntl, "ioctl", lambda *_: 0)
    lock = tmp_path / "uart.lock"
    with pytest.raises(DeviceError, match="vendor_source_hash_mismatch"):
        implementation.open_vendor_device("/test/uart", str(lock))
    assert not port.closed
    monkeypatch.setattr(
        implementation,
        "VENDOR_SOURCE_SHA256",
        hashlib.sha256(source.encode()).hexdigest(),
    )
    marker = Path(str(lock) + ".session")
    save_pending(marker, {0x65}, b"\x55\x00")
    adapter = implementation.open_vendor_device("/test/uart", str(lock))
    assert adapter.metadata()["backend"] == "vendor"
    assert adapter.metadata()["pending_addresses"] == "0x65"
    # Crash marker covers all sources while the connection is live.
    assert load_pending(marker)[0] == {entry[0] for entry in QUERY_ADDRESSES.values()}
    with pytest.raises(BlockingIOError):
        implementation.open_vendor_device("/test/uart", str(lock))
    adapter.close()
    assert port.closed and load_pending(marker) == ({0x65}, b"\x55\x00")
    # Only explicit knowledge of a new hardware session clears attribution.
    adapter = implementation.open_vendor_device(
        "/test/uart", str(lock), fresh_hardware_session=True
    )
    assert adapter.metadata()["pending_addresses"] == ""
    adapter.close()
    assert not marker.exists()


def test_validate_zero_battery_is_valid_not_failure_placeholder() -> None:
    frame = bytes([0x55, 0, 9, 0x12, 1, 0, 0xE3, 0, 0xAA])
    assert validate_response(frame, 1, (1,)) == ""


def test_unmodified_library_over_real_pyserial_pty() -> None:
    """Optional integration input is the externally supplied unchanged library.

    Keep vendor code outside this package; CI may provide the versioned source
    artifact via DOGZILLA_VENDOR_SOURCE. No physical device is accessed.
    """
    source = os.environ.get("DOGZILLA_VENDOR_SOURCE")
    if source is None:
        pytest.skip("set DOGZILLA_VENDOR_SOURCE to the unchanged 3.1.9 implementation")
    spec = importlib.util.spec_from_file_location("capture_test_upstream", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert (
        hashlib.sha256(inspect.getsource(module).encode()).hexdigest()
        == VENDOR_SOURCE_SHA256
    )
    factory = cast(VendorFactory, module.DOGZILLA)
    master, slave = os.openpty()
    stop = threading.Event()
    requests: list[bytes] = []
    errors: list[BaseException] = []
    replies = {
        QUERY_ADDRESSES[name][0]: bytes.fromhex(row["frame_hex"])
        for name, row in FIXTURES.items()
    }

    def mcu() -> None:
        buffer = bytearray()
        try:
            while not stop.is_set():
                readable, _, _ = select.select([master], [], [], 0.01)
                if not readable:
                    continue
                buffer.extend(os.read(master, 4096))
                while len(buffer) >= 3 and len(buffer) >= buffer[2]:
                    size = buffer[2]
                    command = bytes(buffer[:size])
                    del buffer[:size]
                    requests.append(command)
                    if command[3] == 2:
                        time.sleep(0.002)
                        os.write(master, replies[command[4]])
        except OSError as exc:
            if not stop.is_set():
                errors.append(exc)

    vendor = factory(port=os.ttyname(slave), baud=115200, verbose=False)
    adapter = VendorAdapter(
        vendor, source_path=source, source_hash=VENDOR_SOURCE_SHA256
    )
    thread = threading.Thread(target=mcu)
    thread.start()
    try:
        for method in QUERY_ADDRESSES:
            sample = adapter.query(method, lambda: False)
            assert sample.valid, (method, sample.error, sample.chunks)
            expected = FIXTURES[method]["vendor_value"]
            if isinstance(expected, str):
                assert sample.text == expected
            elif isinstance(expected, list):
                assert sample.values == tuple(expected)
            else:
                assert sample.values == (float(expected),)
        chunks = adapter.stop()
        assert [chunk.data[4] for chunk in chunks if chunk.op == "write"] == [
            0x30,
            0x31,
            0x3C,
            0x32,
        ]
        assert all(
            not validate_response(
                bytes.fromhex(row["frame_hex"]),
                QUERY_ADDRESSES[name][0],
                QUERY_ADDRESSES[name][1],
            )
            for name, row in FIXTURES.items()
        )
    finally:
        stop.set()
        thread.join(timeout=1)
        adapter.close()
        os.close(slave)
        os.close(master)
        sys.modules.pop(spec.name, None)
    assert not thread.is_alive() and not errors
