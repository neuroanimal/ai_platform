
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Configuration model for NLP analysis provenance."""

from __future__ import annotations

from pydantic import ConfigDict, field_validator

from ..model.base import ActorType, NLPModel


class NLPProvenanceConfigV2(NLPModel):
    """
    Declarative provenance configuration.

    Provider identity and provenance actor identity are deliberately
    independent. No implicit actor_id is derived from provider_id.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )

    actor_type: ActorType = ActorType.MODEL

    actor_id: str | None = None

    method: str | None = None

    notes: str | None = None

    @field_validator("actor_id", "method", "notes")
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not value:
            raise ValueError("Value must not be blank.")

        return value


__all__ = [
    "NLPProvenanceConfigV2",
]

