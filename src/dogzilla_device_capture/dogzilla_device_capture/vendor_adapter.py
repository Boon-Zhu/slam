"""Observe and interrupt an unchanged DOGZILLALib instance.

The MCU protocol has no request identifier. An incomplete request remains
outstanding until its complete late response is consumed. Its address is not
queried again in the meantime. Pending attribution survives connection reopen.
"""

from __future__ import annotations

import fcntl
import hashlib
import importlib
import inspect
import json
import math
import os
import stat
import struct
import termios
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

from .contracts import DeviceError, Feedback, SerialChunk

VENDOR_SOURCE_SHA256 = (
    "3d05141c71b1066e2274cb0d842bd45b328c6d57a9032b7484494433b185585d"
)
QUERY_ADDRESSES = {
    "read_battery": (0x01, (1,)),
    "read_version": (0x07, (10,)),
    "read_motor": (0x50, (12, 15)),
    "read_roll": (0x62, (4,)),
    "read_pitch": (0x63, (4,)),
    "read_yaw": (0x64, (4,)),
    "read_imu_raw": (0x65, (24,)),
}


class SerialPort(Protocol):
    timeout: float | None
    write_timeout: float | None

    def read(self, size: int = 1) -> bytes: ...
    def read_all(self) -> bytes: ...
    def write(self, data: bytes) -> int: ...
    def inWaiting(self) -> int: ...
    def close(self) -> None: ...
    def fileno(self) -> int: ...


class Vendor(Protocol):
    ser: SerialPort
    rx_FLAG: int
    rx_COUNT: int
    rx_ADDR: int
    rx_LEN: int
    rx_data: bytearray

    def read_battery(self) -> object: ...
    def read_version(self) -> object: ...
    def read_motor(self) -> object: ...
    def read_roll(self) -> object: ...
    def read_pitch(self) -> object: ...
    def read_yaw(self) -> object: ...
    def read_imu_raw(self) -> object: ...
    def move_x(self, value: int) -> None: ...
    def turn(self, value: int) -> None: ...
    def stop(self) -> None: ...


class VendorFactory(Protocol):
    def __call__(self, *, port: str, baud: int, verbose: bool) -> Vendor: ...


class QueryInterrupted(Exception):
    pass


class QueryTimeout(Exception):
    pass


class SerialTrace:
    """Small serial facade; never performs concurrent serial operations."""

    def __init__(
        self,
        port: SerialPort,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.port = port
        self.monotonic_ns = monotonic_ns
        self.sleep = sleep
        self.chunks: list[SerialChunk] = []
        self.interrupt: Callable[[], bool] = lambda: False
        self.deadline_ns: int | None = None
        self.port.timeout = 0.005
        self.port.write_timeout = 0.05

    @property
    def timeout(self) -> float | None:
        return self.port.timeout

    @timeout.setter
    def timeout(self, value: float | None) -> None:
        self.port.timeout = value

    @property
    def write_timeout(self) -> float | None:
        return self.port.write_timeout

    @write_timeout.setter
    def write_timeout(self, value: float | None) -> None:
        self.port.write_timeout = value

    def _check(self) -> None:
        if self.deadline_ns is None:
            return
        if self.interrupt():
            raise QueryInterrupted("query_interrupted")
        if self.monotonic_ns() >= self.deadline_ns:
            raise QueryTimeout("query_timeout")

    def _record(self, op: str, data: bytes) -> None:
        self.chunks.append(SerialChunk(op, self.monotonic_ns(), data))

    def write(self, data: bytes | list[int]) -> int:
        self._check()
        payload = bytes(data)
        self._record("write_request", payload)
        try:
            written = self.port.write(payload)
        except Exception:
            self._record("write_failed_unknown_count", payload)
            raise
        if not 0 <= written <= len(payload):
            raise OSError("invalid_serial_write_count")
        self._record("write", payload[:written])
        if written != len(payload):
            raise OSError(f"short_serial_write:{written}/{len(payload)}")
        return written

    def read(self, size: int = 1) -> bytes:
        self._check()
        data = self.port.read(size)
        self._record("read", data)
        self._check()
        return data

    def read_all(self) -> bytes:
        self._check()
        data = self.port.read_all()
        self._record("read_all_discard", data)
        self._check()
        return data

    def flushInput(self) -> None:
        self._check()
        # Drain a bounded snapshot instead of losing bytes in tcflush. Bytes
        # arriving afterwards remain available and frame validation sees them.
        data = self.port.read(self.port.inWaiting())
        self._record("flush_input_discard", data)
        self._check()

    def inWaiting(self) -> int:
        self._check()
        count = self.port.inWaiting()
        if count == 0:
            self.sleep(0.001)
            self._check()
        return count

    def fileno(self) -> int:
        return self.port.fileno()

    def close(self) -> None:
        self.port.close()


def validate_response(data: bytes, address: int, payload_sizes: tuple[int, ...]) -> str:
    """Return a reason, or empty string for exactly one matching full frame."""
    if not data:
        return "no_response"
    if len(data) < 8 or data[:2] != b"\x55\x00" or data[-2:] != b"\x00\xaa":
        return "frame_boundary"
    if data[2] != len(data):
        return "frame_length"
    if data[3] != 0x12:
        return "response_type"
    if data[4] != address:
        return "response_address"
    if len(data) - 8 not in payload_sizes:
        return "payload_length"
    if data[-3] != 255 - sum(data[2:-3]) % 256:
        return "checksum"
    return ""


class VendorAdapter:
    """An adapter instance belongs to its creating hardware worker thread."""

    def __init__(
        self,
        vendor: Vendor,
        *,
        source_path: str = "injected-test-vendor",
        source_hash: str = "",
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        wall_ns: Callable[[], int] = time.time_ns,
        sleep: Callable[[float], None] = time.sleep,
        lock_fd: int | None = None,
        exclusive: bool = False,
        recovery_marker: Path | None = None,
        pending_addresses: set[int] | None = None,
        partial_response: bytes = b"",
    ) -> None:
        self._owner = threading.get_ident()
        self._vendor = vendor
        self._trace = SerialTrace(vendor.ser, monotonic_ns, sleep)
        self._vendor.ser = self._trace
        self._mono_ns = monotonic_ns
        self._wall_ns = wall_ns
        self._sequence = 0
        self._pending_addresses = set(pending_addresses or ())
        self._wire_buffer = bytearray(partial_response)
        self._source_path = source_path
        self._source_hash = source_hash
        self._lock_fd = lock_fd
        self._exclusive = exclusive
        self._closed = False
        self._recovery_marker = recovery_marker

    def _check_owner(self) -> None:
        if self._closed:
            raise DeviceError("device_closed")
        if threading.get_ident() != self._owner:
            raise DeviceError("serial_access_from_non_owner_thread")

    def metadata(self) -> dict[str, str]:
        return {
            "backend": "vendor",
            "vendor_library": "DOGZILLALib",
            "vendor_version": "3.1.9",
            "vendor_source_path": self._source_path,
            "vendor_source_sha256": self._source_hash,
            "query_timeout_s": "1.0",
            "read_timeout_s": "0.005",
            "write_timeout_s": "0.05",
            "attribution_policy": "no same-address requery until outstanding reply consumed; pending state survives reconnect",
            "protocol_assumption": "one response per query; no unsolicited or duplicated response frames",
            "pending_addresses": ",".join(
                f"0x{address:02x}" for address in sorted(self._pending_addresses)
            ),
            "recovery_state_path": str(self._recovery_marker or ""),
            "timestamp_semantics": "host request and receive times, not MCU sample times",
            "units": "vendor conversions only; axes and physical units unverified",
        }

    def _reset_parser(self) -> None:
        self._vendor.rx_FLAG = 0
        self._vendor.rx_COUNT = 0
        self._vendor.rx_ADDR = 0
        self._vendor.rx_LEN = 0
        self._vendor.rx_data = bytearray(50)

    def _received_frames(self, chunks: tuple[SerialChunk, ...]) -> list[bytes]:
        self._wire_buffer.extend(
            b"".join(
                chunk.data
                for chunk in chunks
                if chunk.op
                in ("read", "read_all_discard", "flush_input_discard", "late_read")
            )
        )
        frames: list[bytes] = []
        while self._wire_buffer:
            if self._wire_buffer[0] != 0x55:
                del self._wire_buffer[0]
                continue
            if len(self._wire_buffer) < 3:
                break
            length = self._wire_buffer[2]
            if self._wire_buffer[1] != 0 or not 8 <= length <= 58:
                del self._wire_buffer[0]
                continue
            if len(self._wire_buffer) < length:
                break
            frame = bytes(self._wire_buffer[:length])
            if validate_response(frame, frame[4], (length - 8,)):
                del self._wire_buffer[0]
                continue
            del self._wire_buffer[:length]
            frames.append(frame)
        return frames

    def _consume_pending(self, frames: list[bytes]) -> set[int]:
        resolved: set[int] = set()
        for frame in frames:
            address = frame[4]
            for expected, sizes in QUERY_ADDRESSES.values():
                if (
                    address == expected
                    and address in self._pending_addresses
                    and not validate_response(frame, address, sizes)
                ):
                    self._pending_addresses.remove(address)
                    resolved.add(address)
        return resolved

    def query(self, method: str, interrupt: Callable[[], bool]) -> Feedback:
        self._check_owner()
        if method not in QUERY_ADDRESSES:
            raise ValueError(f"unsupported_query:{method}")
        address, sizes = QUERY_ADDRESSES[method]
        self._sequence += 1
        start = self._mono_ns()
        wall = self._wall_ns()
        self._trace.chunks = []
        self._trace.interrupt = interrupt
        self._trace.deadline_ns = start + 1_000_000_000
        result: object = None
        error = ""
        self._reset_parser()
        if address in self._pending_addresses:
            try:
                self._trace._check()
                data = self._trace.port.read(self._trace.port.inWaiting())
                self._trace._record("late_read", data)
                frames = self._received_frames(tuple(self._trace.chunks))
                resolved = self._consume_pending(frames)
                error = (
                    "late_response_consumed"
                    if address in resolved
                    else "attribution_uncertain_pending_response"
                )
            except QueryInterrupted:
                error = "interrupted"
            except OSError as exc:
                error = f"serial_error:{type(exc).__name__}:{exc}"
            finally:
                self._trace.deadline_ns = None
                self._trace.interrupt = lambda: False
            return Feedback(
                method,
                self._sequence,
                wall,
                self._wall_ns(),
                start,
                self._mono_ns(),
                tuple(self._trace.chunks),
                error=error,
            )
        methods: dict[str, Callable[[], object]] = {
            "read_battery": self._vendor.read_battery,
            "read_version": self._vendor.read_version,
            "read_motor": self._vendor.read_motor,
            "read_roll": self._vendor.read_roll,
            "read_pitch": self._vendor.read_pitch,
            "read_yaw": self._vendor.read_yaw,
            "read_imu_raw": self._vendor.read_imu_raw,
        }
        try:
            result = methods[method]()
        except QueryInterrupted:
            error = "interrupted"
        except QueryTimeout:
            error = "timeout"
        except OSError as exc:
            error = f"serial_error:{type(exc).__name__}:{exc}"
        except (ValueError, IndexError, TypeError, struct.error) as exc:
            error = f"query_error:{type(exc).__name__}:{exc}"
        finally:
            self._trace.deadline_ns = None
            self._trace.interrupt = lambda: False
            self._reset_parser()
        chunks = tuple(self._trace.chunks)
        response = b"".join(chunk.data for chunk in chunks if chunk.op == "read")
        frame_error = validate_response(response, address, sizes)
        frames = self._received_frames(chunks)
        self._consume_pending(frames)
        # Pre-request flush bytes may contain an old same-address frame. They
        # must not discharge the new request if it later times out.
        current_rx = b"".join(
            chunk.data for chunk in chunks if chunk.op in ("read", "read_all_discard")
        )
        complete_reply = any(
            not validate_response(
                current_rx[offset : offset + current_rx[offset + 2]], address, sizes
            )
            for offset in range(max(0, len(current_rx) - 7))
        )
        if not error:
            error = frame_error
        # Pre-query interruption cannot create an outstanding MCU response.
        if (
            error
            and not complete_reply
            and any(
                chunk.op in ("write", "write_failed_unknown_count") and chunk.data
                for chunk in chunks
            )
        ):
            self._pending_addresses.add(address)
        values: tuple[float, ...] = ()
        text = ""
        if isinstance(result, str):
            text = result
        elif isinstance(result, (int, float)):
            values = (float(result),)
        elif isinstance(result, (tuple, list)) and all(
            isinstance(value, (int, float)) for value in result
        ):
            values = tuple(float(value) for value in result)
        if values and not all(math.isfinite(value) for value in values) and not error:
            error = "nonfinite_vendor_value"
        if result is None and not error:
            error = "missing_vendor_value"
        return Feedback(
            method=method,
            sequence=self._sequence,
            wall_start_ns=wall,
            wall_end_ns=self._wall_ns(),
            mono_start_ns=start,
            mono_end_ns=self._mono_ns(),
            chunks=chunks,
            values=values,
            text=text,
            valid=not error,
            error=error,
        )

    def _command(self, command: Callable[[], None]) -> tuple[SerialChunk, ...]:
        self._check_owner()
        self._trace.chunks = []
        try:
            command()
        except Exception as exc:
            raise DeviceError(
                f"command_error:{type(exc).__name__}:{exc}", tuple(self._trace.chunks)
            ) from exc
        return tuple(self._trace.chunks)

    def move(self, action: str, magnitude: int) -> tuple[SerialChunk, ...]:
        if type(magnitude) is not int:
            raise ValueError("magnitude_must_be_integer")
        if action == "forward" and 1 <= magnitude <= 20:
            return self._command(lambda: self._vendor.move_x(magnitude))
        if action in ("left", "right") and 30 <= magnitude <= 70:
            signed = magnitude if action == "left" else -magnitude
            return self._command(lambda: self._vendor.turn(signed))
        raise ValueError("invalid_motion")

    def stop(self) -> tuple[SerialChunk, ...]:
        return self._command(self._vendor.stop)

    def close(self) -> None:
        if self._closed:
            return
        self._check_owner()
        try:
            if self._exclusive:
                fcntl.ioctl(self._trace.fileno(), termios.TIOCNXCL)
        finally:
            try:
                self._trace.close()
            finally:
                self._closed = True
                try:
                    if self._recovery_marker is not None:
                        if self._pending_addresses:
                            save_pending(
                                self._recovery_marker,
                                self._pending_addresses,
                                bytes(self._wire_buffer),
                            )
                        else:
                            self._recovery_marker.unlink(missing_ok=True)
                finally:
                    if self._lock_fd is not None:
                        os.close(self._lock_fd)
                        self._lock_fd = None


def save_pending(path: Path, addresses: set[int], partial: bytes) -> None:
    """Write only during open/close, never while serving motion deadlines."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(
            {"pending_addresses": sorted(addresses), "partial_hex": partial.hex()}
        )
    )
    temporary.replace(path)


def load_pending(path: Path) -> tuple[set[int], bytes]:
    if not path.exists():
        return set(), b""
    addresses = {value[0] for value in QUERY_ADDRESSES.values()}
    try:
        data = json.loads(path.read_text())
        pending = data["pending_addresses"]
        if not isinstance(pending, list) or any(
            type(x) is not int or x not in addresses for x in pending
        ):
            raise ValueError("invalid_pending_addresses")
        partial = bytes.fromhex(data["partial_hex"])
        if len(partial) > 58:
            raise ValueError("invalid_partial_frame")
        return set(pending), partial
    except (ValueError, KeyError, TypeError, AttributeError):
        # Unreadable attribution metadata must not silently grant freshness.
        return addresses, b""


def check_device_holders(port: str) -> None:
    """Inspect the host PID namespace; fail if visibility is incomplete.

    Hardware containers must run with --pid=host and CAP_SYS_PTRACE to inspect
    other users' /proc descriptors, while the shared lock directory is mounted.
    This does not kill processes or claim to prevent privileged manual bypass.
    """
    if Path("/proc/1/comm").read_text().strip() not in ("systemd", "init"):
        raise DeviceError(
            "host_pid_namespace_required: run hardware container with --pid=host"
        )
    target = Path(port).stat()
    if not stat.S_ISCHR(target.st_mode):
        raise DeviceError("serial_path_is_not_character_device")
    own_pid = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == own_pid:
            continue
        try:
            for fd in (entry / "fd").iterdir():
                try:
                    actual = fd.stat()
                    if (
                        stat.S_ISCHR(actual.st_mode)
                        and actual.st_rdev == target.st_rdev
                    ):
                        raise DeviceError(f"serial_already_owned:pid={entry.name}")
                except FileNotFoundError:
                    continue
        except FileNotFoundError:
            continue
        except PermissionError as exc:
            raise DeviceError(
                "cannot_inspect_host_fds: host preflight/permissions required"
            ) from exc


def open_vendor_device(
    port: str = "/dev/ttyAMA0",
    lock_path: str = "/run/lock/dogzilla-ttyAMA0.lock",
    fresh_hardware_session: bool = False,
) -> VendorAdapter:
    """Open the verified library on the caller's hardware worker thread."""
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    vendor: Vendor | None = None
    exclusive = False
    marker = Path(lock_path + ".session")
    marker_created = False
    prior_marker: bytes | None = None
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        check_device_holders(port)
        package = importlib.import_module("DOGZILLALib")
        factory = cast(VendorFactory, package.DOGZILLA)
        module = inspect.getmodule(factory)
        if module is None or module.__file__ is None:
            raise DeviceError("cannot_locate_vendor_implementation")
        source_hash = hashlib.sha256(inspect.getsource(module).encode()).hexdigest()
        if source_hash != VENDOR_SOURCE_SHA256:
            raise DeviceError(f"vendor_source_hash_mismatch:{source_hash}")
        prior_marker = marker.read_bytes() if marker.exists() else None
        pending, partial = (
            (set(), b"") if fresh_hardware_session else load_pending(marker)
        )
        # A crash can happen during any query. Conservatively reserve all
        # response addresses on disk; orderly close narrows this to reality.
        save_pending(marker, {value[0] for value in QUERY_ADDRESSES.values()}, b"")
        marker_created = True
        vendor = factory(port=port, baud=115200, verbose=False)
        fcntl.ioctl(vendor.ser.fileno(), termios.TIOCEXCL)
        exclusive = True
        # Recheck after opening to cover readers racing the first inspection.
        check_device_holders(port)
        return VendorAdapter(
            vendor,
            source_path=module.__file__,
            source_hash=source_hash,
            lock_fd=lock_fd,
            exclusive=True,
            recovery_marker=marker,
            pending_addresses=pending,
            partial_response=partial,
        )
    except BaseException:
        try:
            if vendor is not None:
                if exclusive:
                    fcntl.ioctl(vendor.ser.fileno(), termios.TIOCNXCL)
                vendor.ser.close()
        finally:
            try:
                if marker_created:
                    if prior_marker is None:
                        marker.unlink(missing_ok=True)
                    else:
                        marker.write_bytes(prior_marker)
            finally:
                os.close(lock_fd)
        raise
