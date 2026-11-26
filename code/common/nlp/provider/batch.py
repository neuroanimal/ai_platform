
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Canonical batch request and response models for NLP providers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from ..model.base import NLPModel
from .capabilities import ProviderCapabilities
from .request import NLPProviderRequest
from .response import NLPProviderResponse
from .validation.conformance import validate_provider_response


class NLPProviderBatchRequest(NLPModel):
    """A collection of independent NLP requests."""

    batch_id: str = Field(min_length=1)
    requests: list[NLPProviderRequest] = Field(min_length=1)

    # Stop scheduling new items after the first failure.
    # Already running items may still finish.
    fail_fast: bool = False

    # Optional upper bound requested by the caller.
    # The provider may apply a lower internal limit.
    max_concurrency: int | None = Field(default=None, gt=0, strict=True)

    @model_validator(mode="after")
    def validate_batch(self) -> "NLPProviderBatchRequest":
        if not self.batch_id.strip():
            raise ValueError("batch_id must not be blank.")

        request_ids = [item.request_id for item in self.requests]

        if len(request_ids) != len(set(request_ids)):
            raise ValueError(
                "A batch must not contain duplicate request_id values."
            )

        return self


class NLPProviderBatchItemError(NLPModel):
    """Serializable error information for one failed batch item."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)

    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class NLPProviderBatchItemResult(NLPModel):
    """Outcome of processing one request in a batch."""

    request_id: str = Field(min_length=1)

    response: NLPProviderResponse | None = None
    error: NLPProviderBatchItemError | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "NLPProviderBatchItemResult":
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank.")

        has_response = self.response is not None
        has_error = self.error is not None

        if has_response == has_error:
            raise ValueError(
                "A batch item must contain exactly one of response or error."
            )

        if (
            self.response is not None
            and self.response.request_id != self.request_id
        ):
            raise ValueError(
                "Batch item request_id must match response.request_id."
            )

        return self


class NLPProviderBatchResponse(NLPModel):
    """Ordered collection of outcomes returned for a batch."""

    batch_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)

    results: list[NLPProviderBatchItemResult] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_results(self) -> "NLPProviderBatchResponse":
        if not self.batch_id.strip():
            raise ValueError("batch_id must not be blank.")

        if not self.provider_id.strip():
            raise ValueError("provider_id must not be blank.")

        request_ids = [item.request_id for item in self.results]

        if len(request_ids) != len(set(request_ids)):
            raise ValueError(
                "Batch response must not contain duplicate request_id values."
            )

        for item in self.results:
            if (
                item.response is not None
                and item.response.provider_id != self.provider_id
            ):
                raise ValueError(
                    "Batch item response provider_id must match "
                    "batch response provider_id."
                )

        return self

    @property
    def succeeded_count(self) -> int:
        """Number of items with a successful response."""
        return sum(item.response is not None for item in self.results)

    @property
    def failed_count(self) -> int:
        """Number of items with an error."""
        return sum(item.error is not None for item in self.results)

    @property
    def is_successful(self) -> bool:
        """Whether every returned item completed successfully.

        It does not say that the provider returned every item of the batch;
        that is checked by validate_provider_batch_response.
        """
        return self.failed_count == 0


class NLPProviderBatchConformanceIssue(NLPModel):
    """One batch request/response conformance problem."""

    code: str
    message: str


class NLPProviderBatchConformanceReport(NLPModel):
    """Result of validating a batch response against its request."""

    is_valid: bool
    issues: list[NLPProviderBatchConformanceIssue] = Field(
        default_factory=list
    )


def validate_provider_batch_response(
    request: NLPProviderBatchRequest,
    capabilities: ProviderCapabilities,
    response: NLPProviderBatchResponse,
) -> NLPProviderBatchConformanceReport:
    """Validate batch identity, coverage and individual responses."""

    issues: list[NLPProviderBatchConformanceIssue] = []

    def add_issue(code: str, message: str) -> None:
        issues.append(
            NLPProviderBatchConformanceIssue(
                code=code,
                message=message,
            )
        )

    if response.batch_id != request.batch_id:
        add_issue(
            "batch_id_mismatch",
            "Batch response batch_id does not match the request.",
        )

    if response.provider_id != capabilities.provider_id:
        add_issue(
            "provider_id_mismatch",
            "Batch response provider_id does not match provider capabilities.",
        )

    requested_ids = {
        item.request_id
        for item in request.requests
    }
    returned_ids = {
        item.request_id
        for item in response.results
    }

    missing_ids = requested_ids - returned_ids
    unexpected_ids = returned_ids - requested_ids

    if missing_ids:
        add_issue(
            "missing_batch_items",
            f"Batch response is missing request IDs: {sorted(missing_ids)}.",
        )

    if unexpected_ids:
        add_issue(
            "unexpected_batch_items",
            f"Batch response contains unexpected request IDs: "
            f"{sorted(unexpected_ids)}.",
        )

    requests_by_id = {
        item.request_id: item
        for item in request.requests
    }

    for item in response.results:
        if item.response is None:
            continue

        original_request = requests_by_id.get(item.request_id)

        if original_request is None:
            continue

        report = validate_provider_response(
            original_request,
            capabilities,
            item.response,
        )

        for provider_issue in report.issues:
            add_issue(
                f"item_{item.request_id}_{provider_issue.code}",
                provider_issue.message,
            )

    return NLPProviderBatchConformanceReport(
        is_valid=not issues,
        issues=issues,
    )


__all__ = [
    "NLPProviderBatchRequest",
    "NLPProviderBatchItemError",
    "NLPProviderBatchItemResult",
    "NLPProviderBatchResponse",
    "NLPProviderBatchConformanceIssue",
    "NLPProviderBatchConformanceReport",
    "validate_provider_batch_response",
]

