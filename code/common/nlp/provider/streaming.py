
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Canonical event models for streaming NLP provider execution."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from ..model.base import NLPModel
from ..model.analysis import AnalysisLayer
from .capabilities import ProviderCapabilities
from .request import NLPProviderRequest
from .response import NLPProviderResponse, ProviderDiagnostic
from .validation.conformance import validate_provider_response


class NLPProviderStreamEventType(StrEnum):
    """Supported lifecycle events emitted by an NLP stream."""

    STARTED = "started"
    PROGRESS = "progress"
    RESULT = "result"
    DIAGNOSTIC = "diagnostic"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NLPProviderStreamError(NLPModel):
    """Serializable error payload emitted by a stream."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)

    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class NLPProviderStreamEvent(NLPModel):
    """One ordered event emitted during streaming analysis."""

    stream_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)

    # Starts at zero and increases by one within a stream.
    sequence: int = Field(ge=0, strict=True)

    event_type: NLPProviderStreamEventType

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Optional progress percentage represented as a fraction [0.0, 1.0].
    progress: float | None = Field(default=None, ge=0.0, le=1.0)

    layer: AnalysisLayer | None = None
    message: str | None = None

    response: NLPProviderResponse | None = None
    diagnostic: ProviderDiagnostic | None = None
    error: NLPProviderStreamError | None = None

    @field_validator("stream_id", "request_id")
    @classmethod
    def validate_nonblank_identifiers(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Identifier must not be blank.")
        return value

    @model_validator(mode="after")
    def validate_event_payload(self) -> "NLPProviderStreamEvent":
        event_type = self.event_type

        if (
            self.response is not None
            and self.response.request_id != self.request_id
        ):
            raise ValueError(
                "Stream event request_id must match response.request_id."
            )

        if event_type == NLPProviderStreamEventType.PROGRESS:
            if self.progress is None:
                raise ValueError(
                    "PROGRESS event requires a progress value."
                )

        elif self.progress is not None:
            raise ValueError(
                "Only PROGRESS events may contain a progress value."
            )

        if event_type == NLPProviderStreamEventType.RESULT:
            if self.response is None:
                raise ValueError("RESULT event requires a response.")
        elif self.response is not None:
            raise ValueError(
                "Only RESULT events may contain a response."
            )

        if event_type == NLPProviderStreamEventType.DIAGNOSTIC:
            if self.diagnostic is None:
                raise ValueError(
                    "DIAGNOSTIC event requires a diagnostic."
                )
        elif self.diagnostic is not None:
            raise ValueError(
                "Only DIAGNOSTIC events may contain a diagnostic."
            )

        if event_type == NLPProviderStreamEventType.FAILED:
            if self.error is None:
                raise ValueError("FAILED event requires an error.")
        elif self.error is not None:
            raise ValueError(
                "Only FAILED events may contain an error."
            )

        if event_type in {
            NLPProviderStreamEventType.STARTED,
            NLPProviderStreamEventType.COMPLETED,
            NLPProviderStreamEventType.CANCELLED,
        }:
            if any(
                value is not None
                for value in (
                    self.progress,
                    self.layer,
                    self.response,
                    self.diagnostic,
                    self.error,
                )
            ):
                raise ValueError(
                    f"{event_type.value.upper()} event cannot contain "
                    "progress, layer, response, diagnostic or error payloads."
                )

        return self


class NLPProviderStreamConformanceIssue(NLPModel):
    """One stream event sequence or identity problem."""

    code: str
    message: str


class NLPProviderStreamConformanceReport(NLPModel):
    """Validation result for a collected stream event sequence."""

    is_valid: bool
    issues: list[NLPProviderStreamConformanceIssue] = Field(
        default_factory=list
    )


def validate_provider_stream_events(
    events: list[NLPProviderStreamEvent],
    *,
    stream_id: str,
    request_id: str,
    request: NLPProviderRequest | None = None,
    capabilities: ProviderCapabilities | None = None,
) -> NLPProviderStreamConformanceReport:
    """Validate identity, sequence numbers and terminal event placement.

    With ``request`` and ``capabilities`` every RESULT response is also
    checked by ``validate_provider_response`` (issue codes ``result_<code>``),
    as ``validate_provider_batch_response`` does for batch items.
    """

    issues: list[NLPProviderStreamConformanceIssue] = []

    def add_issue(code: str, message: str) -> None:
        issues.append(
            NLPProviderStreamConformanceIssue(
                code=code,
                message=message,
            )
        )

    if not stream_id.strip():
        raise ValueError("stream_id must not be blank.")

    if not request_id.strip():
        raise ValueError("request_id must not be blank.")

    if not events:
        add_issue(
            "empty_stream",
            "A stream must contain at least one event.",
        )

    terminal_types = {
        NLPProviderStreamEventType.COMPLETED,
        NLPProviderStreamEventType.FAILED,
        NLPProviderStreamEventType.CANCELLED,
    }

    terminal_positions = [
        index
        for index, event in enumerate(events)
        if event.event_type in terminal_types
    ]

    if len(terminal_positions) > 1:
        add_issue(
            "multiple_terminal_events",
            "A stream must contain at most one terminal event.",
        )

    if terminal_positions and terminal_positions[0] != len(events) - 1:
        add_issue(
            "events_after_terminal",
            "No events may follow a terminal event.",
        )

    if not events:
        add_issue(
            "empty_stream",
            "A completed stream must contain at least STARTED and a terminal event.",
        )

    if events and not terminal_positions:
        add_issue(
            "missing_terminal_event",
            "A completed stream must end with COMPLETED, FAILED or CANCELLED.",
        )

    if events and events[0].event_type != NLPProviderStreamEventType.STARTED:
        add_issue(
            "missing_started_event",
            "The first stream event must be STARTED.",
        )

    for index, event in enumerate(events):
        if event.stream_id != stream_id:
            add_issue(
                "stream_id_mismatch",
                f"Event at index {index} has a different stream_id.",
            )

        if event.request_id != request_id:
            add_issue(
                "request_id_mismatch",
                f"Event at index {index} has a different request_id.",
            )

        if event.sequence != index:
            add_issue(
                "invalid_sequence",
                (
                    f"Event at index {index} has sequence "
                    f"{event.sequence}; expected {index}."
                ),
            )

    if request is not None and capabilities is not None:
        for index, event in enumerate(events):
            if event.response is None:
                continue
            report = validate_provider_response(
                request,
                capabilities,
                event.response,
            )
            for provider_issue in report.issues:
                add_issue(
                    f"result_{provider_issue.code}",
                    f"RESULT event at index {index}: {provider_issue.message}",
                )

    return NLPProviderStreamConformanceReport(
        is_valid=not issues,
        issues=issues,
    )


__all__ = [
    "NLPProviderStreamEventType",
    "NLPProviderStreamError",
    "NLPProviderStreamEvent",
    "NLPProviderStreamConformanceIssue",
    "NLPProviderStreamConformanceReport",
    "validate_provider_stream_events",
]

