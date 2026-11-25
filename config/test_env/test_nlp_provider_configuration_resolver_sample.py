from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.nlp.provider import (
    NLPProviderConfigurationLoader,
    NLPProviderConfigurationResolver,
)

registry = PluginRegistry()

# Provider musi być wcześniej jawnie zarejestrowany.
# Rejestracja pozostaje odpowiedzialnością pluginu/lifecycle.

configuration = NLPProviderConfigurationLoader.from_yaml(
    "config/nlp/stanza.yaml"
)

resolver = NLPProviderConfigurationResolver(registry)
resolution = resolver.resolve(configuration)

provider = resolution.provider
fingerprint = resolution.configuration_fingerprint


