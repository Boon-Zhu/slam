"""Pure CLI parsing, independent of ROS and serial hardware."""

from __future__ import annotations

import argparse
import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Arguments:
    command: str
    namespace: str
    timeout_s: float
    magnitude: int | None = None
    duration_s: float | None = None


def positive_seconds(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return value


def parse_arguments(argv: Sequence[str] | None = None) -> Arguments:
    parser = argparse.ArgumentParser(description="Explicit one-shot capture commands")
    parser.add_argument("--namespace", default="/capture/device")
    parser.add_argument("--timeout", type=positive_seconds, default=5.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("stop")
    for command in ("forward", "left", "right"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--input", type=int, required=True, dest="magnitude")
        sub.add_argument("--duration", type=positive_seconds, required=True)
    parsed = parser.parse_args(argv)
    magnitude = getattr(parsed, "magnitude", None)
    if magnitude is not None:
        low, high = (1, 20) if parsed.command == "forward" else (30, 70)
        if not low <= magnitude <= high:
            parser.error(f"{parsed.command} input must be in [{low}, {high}]")
    namespace = parsed.namespace.rstrip("/")
    if not namespace.startswith("/") or not namespace:
        parser.error("namespace must be an absolute non-root ROS namespace")
    return Arguments(
        parsed.command,
        namespace,
        parsed.timeout,
        magnitude,
        getattr(parsed, "duration", None),
    )
