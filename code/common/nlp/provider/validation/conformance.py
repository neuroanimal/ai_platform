
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Provider request and response conformance validation."""

from pydantic import Field

from ...model.base import NLPModel
from ...model.analysis import (
    AnalysisLayer,
    AnalysisLayerExecutionStatus,
    NLPAnalysis,
)
from ..capabilities import ProviderCapabilities
from ..request import NLPProviderRequest
from ..response import NLPProviderResponse


class ProviderConformanceIssue(NLPModel):
    code: str
    message: str


class ProviderConformanceReport(NLPModel):
    is_valid: bool
    issues: list[ProviderConformanceIssue] = Field(default_factory=list)


def _report(
    issues: list[ProviderConformanceIssue],
) -> ProviderConformanceReport:
    return ProviderConformanceReport(
        is_valid=not issues,
        issues=issues,
    )


def _add_issue(
    issues: list[ProviderConformanceIssue],
    code: str,
    message: str,
) -> None:
    issues.append(
        ProviderConformanceIssue(
            code=code,
            message=message,
        )
    )


def _get_requested_text(request: NLPProviderRequest) -> str:
    for version in request.document.text_versions:
        if version.text_version_id == request.text_version_id:
            return version.text

    # NLPProviderRequest already validates this reference.
    raise ValueError(
        f"Unknown text version: {request.text_version_id}"
    )


def validate_provider_request(
    request: NLPProviderRequest,
    capabilities: ProviderCapabilities,
) -> ProviderConformanceReport:
    """Check whether a provider declares support for a request."""

    issues: list[ProviderConformanceIssue] = []

    unsupported_layers = (
        set(request.requested_layers)
        - set(capabilities.supported_layers)
    )

    if unsupported_layers:
        names = sorted(layer.value for layer in unsupported_layers)

        _add_issue(
            issues,
            "unsupported_requested_layers",
            f"Provider does not declare support for layers: {names}.",
        )

    if capabilities.max_input_characters is not None:
        text_length = len(_get_requested_text(request))

        if text_length > capabilities.max_input_characters:
            _add_issue(
                issues,
                "input_exceeds_provider_limit",
                (
                    f"Input contains {text_length} characters; "
                    f"provider limit is "
                    f"{capabilities.max_input_characters}."
                ),
            )

    return _report(issues)


def validate_provider_response(
    request: NLPProviderRequest,
    capabilities: ProviderCapabilities,
    response: NLPProviderResponse,
) -> ProviderConformanceReport:
    """Check whether a provider response conforms to its request."""

    issues: list[ProviderConformanceIssue] = []
    analysis: NLPAnalysis = response.analysis

    if response.request_id != request.request_id:
        _add_issue(
            issues,
            "request_id_mismatch",
            "Response request_id does not match the request.",
        )

    if response.provider_id != capabilities.provider_id:
        _add_issue(
            issues,
            "provider_id_mismatch",
            "Response provider_id does not match declared capabilities.",
        )

    if analysis.document_id != request.document.document_id:
        _add_issue(
            issues,
            "document_id_mismatch",
            "Analysis document_id does not match the request document.",
        )

    if analysis.text_version_id != request.text_version_id:
        _add_issue(
            issues,
            "text_version_id_mismatch",
            "Analysis text_version_id does not match the requested version.",
        )

    if analysis.provider is None:
        _add_issue(
            issues,
            "missing_provider_metadata",
            "Analysis must contain provider metadata.",
        )
    else:
        if analysis.provider.provider_id != capabilities.provider_id:
            _add_issue(
                issues,
                "analysis_provider_id_mismatch",
                "Analysis provider metadata identifies a different provider.",
            )

        reported_version = analysis.provider.provider_version

        if (
            reported_version is not None
            and reported_version != capabilities.provider_version
        ):
            _add_issue(
                issues,
                "provider_version_mismatch",
                (
                    "Analysis provider version does not match "
                    "declared provider capabilities."
                ),
            )

    completed = analysis.completed_layers
    unavailable = analysis.unavailable_layers

    if len(completed) != len(set(completed)):
        _add_issue(
            issues,
            "duplicate_completed_layers",
            "Analysis contains duplicate completed layers.",
        )

    if len(unavailable) != len(set(unavailable)):
        _add_issue(
            issues,
            "duplicate_unavailable_layers",
            "Analysis contains duplicate unavailable layers.",
        )

    completed_set = set(completed)
    unavailable_set = set(unavailable)

    overlap = completed_set & unavailable_set

    if overlap:
        names = sorted(layer.value for layer in overlap)

        _add_issue(
            issues,
            "completed_unavailable_overlap",
            f"Layers cannot be both completed and unavailable: {names}.",
        )

    reported_layers = completed_set | unavailable_set
    requested_layers = set(request.requested_layers)
    supported_layers = set(capabilities.supported_layers)

    unrequested = reported_layers - requested_layers

    if unrequested:
        names = sorted(layer.value for layer in unrequested)

        _add_issue(
            issues,
            "unrequested_layers_reported",
            f"Analysis reports layers that were not requested: {names}.",
        )

    # unsupported = reported_layers - supported_layers
    #
    # if unsupported:
    #     names = sorted(layer.value for layer in unsupported)
    #
    #     _add_issue(
    #         issues,
    #         "unsupported_layers_reported",
    #         f"Analysis reports layers not declared by the provider: {names}.",
    #     )

    unsupported_completed = completed_set - supported_layers

    if unsupported_completed:
        names = sorted(
            layer.value
            for layer in unsupported_completed
        )

        _add_issue(
            issues,
            "unsupported_completed_layers",
            (
                "Analysis reports unsupported layers as completed: "
                f"{names}."
            ),
        )

    if not request.allow_partial:
        missing = requested_layers - completed_set

        if missing:
            names = sorted(layer.value for layer in missing)

            _add_issue(
                issues,
                "incomplete_analysis",
                (
                    "Partial results were not allowed, but the provider "
                    f"did not complete all requested layers: {names}."
                ),
            )

    # Layer execution status validation.
    layer_executions = analysis.layer_executions

    if layer_executions:
        execution_layers = [
            item.layer
            for item in layer_executions
        ]

        if len(execution_layers) != len(set(execution_layers)):
            _add_issue(
                issues,
                "duplicate_layer_executions",
                "Analysis contains duplicate layer execution records.",
            )

        execution_map = {
            item.layer: item
            for item in layer_executions
        }

        execution_set = set(execution_layers)

        unrequested_executions = execution_set - requested_layers

        if unrequested_executions:
            names = sorted(
                layer.value
                for layer in unrequested_executions
            )

            _add_issue(
                issues,
                "unrequested_layer_executions",
                (
                    "Analysis contains execution records for "
                    f"unrequested layers: {names}."
                ),
            )

        missing_executions = requested_layers - execution_set

        if missing_executions:
            names = sorted(
                layer.value
                for layer in missing_executions
            )

            _add_issue(
                issues,
                "missing_layer_executions",
                (
                    "Analysis does not contain execution records "
                    f"for requested layers: {names}."
                ),
            )

        completed_from_status = {
            layer
            for layer, item in execution_map.items()
            if item.status == AnalysisLayerExecutionStatus.COMPLETED
        }

        unavailable_from_status = {
            layer
            for layer, item in execution_map.items()
            if item.status == AnalysisLayerExecutionStatus.UNAVAILABLE
        }

        if completed_from_status != completed_set:
            _add_issue(
                issues,
                "completed_layer_execution_mismatch",
                (
                    "completed_layers must match layers whose "
                    "execution status is COMPLETED."
                ),
            )

        if unavailable_from_status != unavailable_set:
            _add_issue(
                issues,
                "unavailable_layer_execution_mismatch",
                (
                    "unavailable_layers must match layers whose "
                    "execution status is UNAVAILABLE."
                ),
            )

        # A requested layer the provider does not support must still get an
        # execution record (see missing_layer_executions above) - with status
        # UNAVAILABLE. Only other statuses on unsupported layers are wrong;
        # otherwise a correct partial response could never be valid.
        unsupported_executions = {
            layer
            for layer in execution_set - supported_layers
            if execution_map[layer].status
            != AnalysisLayerExecutionStatus.UNAVAILABLE
        }

        if unsupported_executions:
            names = sorted(
                layer.value
                for layer in unsupported_executions
            )

            _add_issue(
                issues,
                "unsupported_layer_executions",
                (
                    "Analysis reports execution of unsupported layers "
                    f"(only status UNAVAILABLE is allowed for them): {names}."
                ),
            )

    return _report(issues)

