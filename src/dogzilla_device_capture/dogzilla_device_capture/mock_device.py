"""Synthetic backend for software tests; never imports the vendor/serial modules."""

from __future__ import annotations

import struct
import threading
import time
from collections.abc import Callable

from .contracts import Feedback, SerialChunk


class MockDevice:
    def __init__(self, query_delay_s: float = 0.002) -> None:
        self._owner = threading.get_ident()
        self._sequence = 0
        self._closed = False
        self._query_delay_s = query_delay_s

    def _check_owner(self) -> None:
        if threading.get_ident() != self._owner:
            raise RuntimeError("mock device accessed outside its owner thread")
        if self._closed:
            raise RuntimeError("mock device is closed")

    def metadata(self) -> dict[str, str]:
        self._check_owner()
        return {"backend": "mock", "data_origin": "synthetic, never hardware evidence"}

    def query(self, method: str, interrupt: Callable[[], bool]) -> Feedback:
        self._check_owner()
        self._sequence += 1
        wall_start, mono_start = time.time_ns(), time.monotonic_ns()
        mapping: dict[str, tuple[int, bytes, tuple[float, ...], str]] = {
            "read_battery": (1, bytes([50]), (50.0,), ""),
            "read_version": (7, b"MOCK-ONLY\0", (), "MOCK-ONLY"),
            "read_motor": (80, bytes([128] * 12 + [0, 255, 0]), (0.0,) * 12, ""),
            "read_imu_raw": (
                101,
                struct.pack("<6h3f", 0, 0, -16384, 0, 0, 0, 0, 0, 0),
                (0.0, 0.0, -9.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                "",
            ),
            "read_roll": (98, struct.pack("<f", 0), (0.0,), ""),
            "read_pitch": (99, struct.pack("<f", 0), (0.0,), ""),
            "read_yaw": (100, struct.pack("<f", 0), (0.0,), ""),
        }
        addr, payload, values, text = mapping[method]
        read_length = 12 if method == "read_motor" else len(payload)
        request = bytes(
            [
                85,
                0,
                9,
                2,
                addr,
                read_length,
                255 - (11 + addr + read_length) % 256,
                0,
                170,
            ]
        )
        chunks = [SerialChunk("write", mono_start, request)]
        deadline = time.monotonic() + self._query_delay_s
        interrupted = False
        while time.monotonic() < deadline:
            if interrupt():
                interrupted = True
                break
            time.sleep(0.0005)
        if interrupt():
            interrupted = True
        if not interrupted:
            body = bytes([len(payload) + 8, 18, addr]) + payload
            response = b"\x55\x00" + body + bytes([255 - sum(body) % 256, 0, 170])
            chunks.append(SerialChunk("read", time.monotonic_ns(), response))
        return Feedback(
            method,
            self._sequence,
            wall_start,
            time.time_ns(),
            mono_start,
            time.monotonic_ns(),
            tuple(chunks),
            () if interrupted else values,
            "" if interrupted else text,
            not interrupted,
            "interrupted" if interrupted else "",
        )

    def move(self, action: str, magnitude: int) -> tuple[SerialChunk, ...]:
        self._check_owner()
        return (
            SerialChunk(
                "mock_write", time.monotonic_ns(), f"{action}:{magnitude}".encode()
            ),
        )

    def stop(self) -> tuple[SerialChunk, ...]:
        self._check_owner()
        return tuple(
            SerialChunk("mock_write", time.monotonic_ns(), f"{axis}:0".encode())
            for axis in ("x", "y", "mark_time", "turn")
        )

    def close(self) -> None:
        self._check_owner()
        self._closed = True
