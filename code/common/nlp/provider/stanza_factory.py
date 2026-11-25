
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Configuration adapter for the Polish Stanza provider."""

from __future__ import annotations

from ai_platform.common.nlp.provider.configuration_v2 import (
    NLPDownloadPolicy,
    NLPProviderConfigurationV2,
)
from ai_platform.common.nlp.provider.errors import (
    NLPProviderConfigurationError,
)
from ai_platform.common.nlp.provider.stanza_provider import (
    PROVIDER_ID,
    StanzaPolishProvider,
)


class StanzaPolishEngineAdapter:
    """
    Translate canonical NLP configuration into Stanza provider settings.

    Supported configuration:
    - engine.engine_name: stanza
    - model.package: Stanza package identifier
    - model.model_dir: explicit resources directory
    - model.language: pl
    - runtime.device: auto or cpu

    No model downloads are performed.
    """

    @property
    def engine_name(self) -> str:
        return "stanza"

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

        if configuration.provider_id != PROVIDER_ID:
            raise NLPProviderConfigurationError(
                "Stanza adapter only supports provider_id "
                f"'{PROVIDER_ID}'.",
                provider_id=configuration.provider_id,
            )

        engine = configuration.engine
        model = configuration.model
        runtime = configuration.runtime

        if engine.engine_name.casefold() != self.engine_name:
            raise NLPProviderConfigurationError(
                "Stanza adapter received a different engine_name.",
                provider_id=configuration.provider_id,
            )

        if engine.options:
            raise NLPProviderConfigurationError(
                "Stanza adapter does not currently support "
                "custom engine.options.",
                provider_id=configuration.provider_id,
                details={
                    "unsupported_fields": sorted(engine.options.keys()),
                },
            )

        if engine.api_key_env is not None:
            raise NLPProviderConfigurationError(
                "Stanza does not use an API key.",
                provider_id=configuration.provider_id,
            )

        if model is None:
            raise NLPProviderConfigurationError(
                "Stanza requires an explicit model configuration.",
                provider_id=configuration.provider_id,
            )

        # if model.language not in {None, "pl"}:
        if (
            model.language is not None
            and model.language.strip().casefold() != "pl"
        ):
            raise NLPProviderConfigurationError(
                "Stanza Polish provider only supports language 'pl'.",
                provider_id=configuration.provider_id,
                details={
                    "configured_language": model.language,
                },
            )

        if model.model_id not in {None, "pl-default-pdb"}:
            raise NLPProviderConfigurationError(
                "The configured model_id is not supported "
                "by the Stanza Polish adapter.",
                provider_id=configuration.provider_id,
                details={
                    "configured_model_id": model.model_id,
                },
            )

        if model.version is not None:
            raise NLPProviderConfigurationError(
                "Explicit Stanza model version selection "
                "is not supported by this adapter yet.",
                provider_id=configuration.provider_id,
            )

        if model.download_policy != NLPDownloadPolicy.NEVER:
            raise NLPProviderConfigurationError(
                "Stanza adapter requires download_policy='never'. "
                "Model downloads must be performed explicitly "
                "outside provider initialization.",
                provider_id=configuration.provider_id,
                details={
                    "download_policy": model.download_policy.value,
                },
            )

        if runtime.device not in {"auto", "cpu"}:
            raise NLPProviderConfigurationError(
                "Stanza adapter currently supports only "
                "'auto' and 'cpu' execution devices.",
                provider_id=configuration.provider_id,
                details={
                    "configured_device": runtime.device,
                },
            )

        if runtime.threads is not None:
            raise NLPProviderConfigurationError(
                "Stanza adapter does not currently apply "
                "runtime.threads.",
                provider_id=configuration.provider_id,
            )

        package = model.package or "default"

        return StanzaPolishProvider(
            model_dir=model.model_dir,
            package=package,
            use_gpu=False,
        )


__all__ = [
    "StanzaPolishEngineAdapter",
]

