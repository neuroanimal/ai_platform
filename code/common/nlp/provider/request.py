
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Canonical request passed to an NLP provider."""

from typing import Any

from pydantic import Field, model_validator

from ..model.base import NLPModel
from ..model.analysis import AnalysisLayer
from ..model.document import NLPDocument


class NLPProviderRequest(NLPModel):
    """Request for processing one document text version."""

    request_id: str = Field(min_length=1)

    document: NLPDocument
    text_version_id: str = Field(min_length=1)

    requested_layers: list[AnalysisLayer] = Field(min_length=1)

    configuration: dict[str, Any] = Field(default_factory=dict)

    allow_partial: bool = True
    include_provider_native: bool = True

    @model_validator(mode="after")
    def validate_request(self) -> "NLPProviderRequest":
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank.")

        if not self.text_version_id.strip():
            raise ValueError("text_version_id must not be blank.")

        if len(self.requested_layers) != len(set(self.requested_layers)):
            raise ValueError("requested_layers must not contain duplicates.")

        available_version_ids = {
            version.text_version_id
            for version in self.document.text_versions
        }

        if self.text_version_id not in available_version_ids:
            raise ValueError(
                f"Text version '{self.text_version_id}' "
                f"does not exist in document "
                f"'{self.document.document_id}'."
            )

        return self

