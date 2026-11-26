
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Configuration adapter for the Polish Stanza provider."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ai_platform.common.nlp.provider.configuration_v2 import (
    NLPDownloadPolicy,
    NLPProviderConfigurationV2,
)
from ai_platform.common.nlp.provider.errors import (
    NLPProviderConfigurationError,
)
from ai_platform.common.nlp.provider.stanza_provider import (
    PROCESSORS,
    PROVIDER_ID,
    StanzaPolishProvider,
)


SUPPORTED_ENGINE_OPTIONS = frozenset({
    "processors",
    "tokenize_batch_size",
})

REQUIRED_PROCESSORS = frozenset({
    "tokenize",
    "mwt",
    "pos",
    "lemma",
    "depparse",
})


class StanzaPolishEngineAdapter:
    """
    Translate canonical NLP configuration into Stanza provider settings.

    Applied engine options:
    - processors
    - tokenize_batch_size

    Applied model settings:
    - package
    - model_dir
    - language
    - model_id consistency

    Applied runtime settings:
    - device='cpu'  -> use_gpu=False
    - device='auto' -> use_gpu=None (Stanza automatic selection)

    Unsupported settings are rejected explicitly.
    """

    @property
    def engine_name(self) -> str:
        return "stanza"

    @staticmethod
    def _configuration_error(
        message: str,
        provider_id: str,
        details: dict[str, Any] | None = None,
    ) -> NLPProviderConfigurationError:
        return NLPProviderConfigurationError(
            message,
            provider_id=provider_id,
            details=details or {},
        )

    @staticmethod
    def _normalize_processors(
        value: Any,
        provider_id: str,
    ) -> str:
        if value is None:
            return PROCESSORS

        if isinstance(value, str):
            processors = [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

        elif isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes),
        ):
            processors = []

            for item in value:
                if not isinstance(item, str):
                    raise NLPProviderConfigurationError(
                        "Every Stanza processor name must be a string.",
                        provider_id=provider_id,
                    )

                normalized = item.strip()

                if not normalized:
                    raise NLPProviderConfigurationError(
                        "Stanza processor names must not be blank.",
                        provider_id=provider_id,
                    )

                processors.append(normalized)

        else:
            raise NLPProviderConfigurationError(
                "Stanza option 'processors' must be a comma-separated "
                "string or a sequence of strings.",
                provider_id=provider_id,
            )

        if not processors:
            raise NLPProviderConfigurationError(
                "Stanza option 'processors' must not be empty.",
                provider_id=provider_id,
            )

        if len(processors) != len(set(processors)):
            raise NLPProviderConfigurationError(
                "Stanza option 'processors' contains duplicates.",
                provider_id=provider_id,
            )

        required_missing = REQUIRED_PROCESSORS.difference(processors)

        if required_missing:
            raise NLPProviderConfigurationError(
                "The configured Stanza pipeline is missing processors "
                "required by the canonical provider mapping.",
                provider_id=provider_id,
                details={
                    "missing_processors": sorted(required_missing),
                    "required_processors": sorted(REQUIRED_PROCESSORS),
                },
            )

        for processor in processors:
            if not processor.replace("_", "").isalnum():
                raise NLPProviderConfigurationError(
                    "Invalid Stanza processor identifier.",
                    provider_id=provider_id,
                    details={"processor": processor},
                )

        return ",".join(processors)

    @staticmethod
    def _validate_engine_options(
        options: dict[str, Any],
        provider_id: str,
    ) -> tuple[str, int]:
        unknown_options = set(options).difference(
            SUPPORTED_ENGINE_OPTIONS
        )

        if unknown_options:
            raise NLPProviderConfigurationError(
                "Stanza adapter received unsupported engine options.",
                provider_id=provider_id,
                details={
                    "unsupported_fields": sorted(unknown_options),
                    "supported_fields": sorted(SUPPORTED_ENGINE_OPTIONS),
                },
            )

        processors = StanzaPolishEngineAdapter._normalize_processors(
            options.get("processors"),
            provider_id,
        )

        tokenize_batch_size = options.get(
            "tokenize_batch_size",
            32,
        )

        if (
            isinstance(tokenize_batch_size, bool)
            or not isinstance(tokenize_batch_size, int)
            or tokenize_batch_size <= 0
        ):
            raise NLPProviderConfigurationError(
                "Stanza option 'tokenize_batch_size' "
                "must be a positive integer.",
                provider_id=provider_id,
                details={
                    "configured_value": tokenize_batch_size,
                },
            )

        return processors, tokenize_batch_size

    def create_provider(
        self,
        configuration: NLPProviderConfigurationV2,
    ) -> StanzaPolishProvider:
        if not isinstance(
            configuration,
            NLPProviderConfigurationV2,
        ):
            raise TypeError(
                "configuration must be NLPProviderConfigurationV2."
            )

        provider_id = configuration.provider_id

        if provider_id != PROVIDER_ID:
            raise self._configuration_error(
                "Stanza adapter only supports provider_id "
                f"'{PROVIDER_ID}'.",
                provider_id,
            )

        engine = configuration.engine
        model = configuration.model
        runtime = configuration.runtime

        if engine.engine_name.casefold() != self.engine_name:
            raise self._configuration_error(
                "Stanza adapter received a different engine_name.",
                provider_id,
            )

        if engine.api_key_env is not None:
            raise self._configuration_error(
                "Stanza does not use an API key.",
                provider_id,
            )

        processors, tokenize_batch_size = (
            self._validate_engine_options(
                engine.options,
                provider_id,
            )
        )

        if model is None:
            raise self._configuration_error(
                "Stanza requires an explicit model configuration.",
                provider_id,
            )

        if (
            model.language is not None
            and model.language.casefold() != "pl"
        ):
            raise self._configuration_error(
                "Stanza Polish provider only supports language 'pl'.",
                provider_id,
                {
                    "configured_language": model.language,
                },
            )

        package = model.package or "default"
        expected_model_id = f"pl-{package}-pdb"

        if (
            model.model_id is not None
            and model.model_id != expected_model_id
        ):
            raise self._configuration_error(
                "Configured model_id does not match the selected "
                "Stanza package.",
                provider_id,
                {
                    "configured_model_id": model.model_id,
                    "expected_model_id": expected_model_id,
                    "package": package,
                },
            )

        if model.version is not None:
            raise self._configuration_error(
                "Explicit Stanza model version selection "
                "is not supported by this adapter yet.",
                provider_id,
                {
                    "configured_version": model.version,
                },
            )

        if model.download_policy != NLPDownloadPolicy.NEVER:
            raise self._configuration_error(
                "Stanza adapter requires download_policy='never'. "
                "Model downloads must be performed explicitly "
                "outside provider initialization.",
                provider_id,
                {
                    "download_policy": model.download_policy.value,
                },
            )

        if runtime.device == "cpu":
            use_gpu: bool | None = False

        elif runtime.device == "auto":
            use_gpu = None

        else:
            raise self._configuration_error(
                "Stanza adapter currently supports runtime.device "
                "values 'auto' and 'cpu'.",
                provider_id,
                {
                    "configured_device": runtime.device,
                },
            )

        if runtime.threads is not None:
            raise self._configuration_error(
                "Stanza adapter does not currently apply runtime.threads.",
                provider_id,
                {
                    "configured_threads": runtime.threads,
                },
            )

        if runtime.batch_size is not None:
            raise self._configuration_error(
                "Stanza Polish provider does not currently support "
                "runtime.batch_size.",
                provider_id,
                {
                    "configured_batch_size": runtime.batch_size,
                },
            )

        if (
            runtime.device == "auto"
            and not runtime.allow_device_fallback
        ):
            raise self._configuration_error(
                "Stanza automatic device selection cannot guarantee "
                "that device fallback is disabled.",
                provider_id,
            )

        return StanzaPolishProvider(
            model_dir=model.model_dir,
            package=package,
            use_gpu=use_gpu,
            processors=processors,
            tokenize_batch_size=tokenize_batch_size,
            device=runtime.device,
            provenance=configuration.provenance,
        )


__all__ = [
    "SUPPORTED_ENGINE_OPTIONS",
    "REQUIRED_PROCESSORS",
    "StanzaPolishEngineAdapter",
]

