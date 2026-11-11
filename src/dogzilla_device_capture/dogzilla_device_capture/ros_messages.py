"""ROS generated-message boundary; domain logic uses typed dataclasses."""

from dogzilla_capture_interfaces.msg import (  # type: ignore[import-untyped]
    CaptureEvent,
    CaptureMetadata,
    CaptureStatus,
)
from dogzilla_capture_interfaces.msg import (
    Feedback as FeedbackMessage,
)
from dogzilla_capture_interfaces.msg import (
    SerialChunk as SerialChunkMessage,
)

from .contracts import Event, Feedback, Metadata, SerialChunk, Status


def chunk_message(chunk: SerialChunk) -> SerialChunkMessage:
    return SerialChunkMessage(op=chunk.op, mono_ns=chunk.mono_ns, data=list(chunk.data))


def feedback_message(session_id: str, value: Feedback) -> FeedbackMessage:
    return FeedbackMessage(
        session_id=session_id,
        method=value.method,
        sequence=value.sequence,
        wall_start_ns=value.wall_start_ns,
        wall_end_ns=value.wall_end_ns,
        mono_start_ns=value.mono_start_ns,
        mono_end_ns=value.mono_end_ns,
        chunks=[chunk_message(chunk) for chunk in value.chunks],
        values=list(value.values),
        text=value.text,
        valid=value.valid,
        error=value.error,
    )


def event_message(session_id: str, value: Event) -> CaptureEvent:
    return CaptureEvent(
        session_id=session_id,
        kind=value.kind,
        request_id=value.request_id,
        wall_ns=value.wall_ns,
        mono_ns=value.mono_ns,
        detail=value.detail,
        chunks=[chunk_message(chunk) for chunk in value.chunks],
    )


def status_message(value: Status) -> CaptureStatus:
    return CaptureStatus(
        session_id=value.session_id,
        state=value.state,
        current_request_id=value.current_request_id,
        enable_motion=value.enable_motion,
        feedback_count=value.feedback_count,
        invalid_feedback_count=value.invalid_feedback_count,
        feedback_paused=value.feedback_paused,
        backpressure_count=value.backpressure_count,
        last_error=value.last_error,
        wall_ns=value.wall_ns,
        mono_ns=value.mono_ns,
    )


def metadata_message(value: Metadata) -> CaptureMetadata:
    keys = sorted(value.entries)
    result = CaptureMetadata(
        session_id=value.session_id,
        wall_ns=value.wall_ns,
        mono_ns=value.mono_ns,
        keys=keys,
        values=[value.entries[key] for key in keys],
        has_firmware=value.firmware is not None,
    )
    if value.firmware is not None:
        result.firmware = feedback_message(value.session_id, value.firmware)
    return result
