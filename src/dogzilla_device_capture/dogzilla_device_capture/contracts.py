"""Typed, ROS-independent contracts for the first-capture device entry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SerialChunk:
    op: str
    mono_ns: int
    data: bytes


@dataclass(frozen=True)
class Feedback:
    method: str
    sequence: int
    wall_start_ns: int
    wall_end_ns: int
    mono_start_ns: int
    mono_end_ns: int
    chunks: tuple[SerialChunk, ...] = ()
    values: tuple[float, ...] = ()
    text: str = ""
    valid: bool = False
    error: str = ""


@dataclass(frozen=True)
class Event:
    kind: str
    request_id: str
    wall_ns: int
    mono_ns: int
    detail: str = ""
    chunks: tuple[SerialChunk, ...] = ()


class DeviceError(Exception):
    """A device operation failed; retain any writes/reads made before failure."""

    def __init__(self, message: str, chunks: tuple[SerialChunk, ...] = ()) -> None:
        super().__init__(message)
        self.chunks = chunks


class Device(Protocol):
    def query(self, method: str, interrupt: Callable[[], bool]) -> Feedback: ...

    def move(self, action: str, magnitude: int) -> tuple[SerialChunk, ...]: ...

    def stop(self) -> tuple[SerialChunk, ...]: ...

    def close(self) -> None: ...

    def metadata(self) -> dict[str, str]: ...


class Clock(Protocol):
    def monotonic_ns(self) -> int: ...

    def time_ns(self) -> int: ...


@dataclass(frozen=True)
class MotionRequest:
    session_id: str
    request_id: str
    action: str
    magnitude: int
    duration_s: float


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str
    request_id: str


@dataclass(frozen=True)
class Status:
    session_id: str
    state: str
    current_request_id: str
    enable_motion: bool
    feedback_count: int
    invalid_feedback_count: int
    feedback_paused: bool
    backpressure_count: int
    last_error: str
    wall_ns: int
    mono_ns: int


@dataclass(frozen=True)
class Metadata:
    session_id: str
    wall_ns: int
    mono_ns: int
    entries: dict[str, str]
    firmware: Feedback | None = None
