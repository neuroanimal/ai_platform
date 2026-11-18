"""
Azure OpenAI adapter (deployment-based Chat Completions API).

Configuration on top of OpenAICompatibleAdapter:

    base_url     "https://<resource>.openai.azure.com"
    deployment   deployment name; defaults to ``model`` (Azure routes by
                 deployment, the ``model`` field in the body is ignored)
    api_version  REST API version, default DEFAULT_API_VERSION
    api_key      or api_key_env (default AZURE_OPENAI_API_KEY); sent in the
                 ``api-key`` header, not as a Bearer token

Microsoft Entra ID tokens can be used instead of a key by passing
``headers={"Authorization": "Bearer <token>"}`` and ``require_api_key=False``.

Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class AzureOpenAIAdapter(OpenAICompatibleAdapter):
    """Chat Completions adapter for an Azure OpenAI deployment."""

    PROVIDER = "azure_openai"
    DEFAULT_API_KEY_ENV = "AZURE_OPENAI_API_KEY"
    REQUIRES_API_KEY = True
    AUTH_HEADER = "api-key"
    AUTH_SCHEME = ""
    DEFAULT_API_PREFIX = "/openai"
    DEFAULT_API_VERSION = "2024-10-21"

    def __init__(self) -> None:
        super().__init__()
        self.deployment = None
        self.api_version = self.DEFAULT_API_VERSION

    def initialize(self, config: Dict[str, Any]) -> None:
        """Accept ``deployment`` as an alias of ``model``, then initialize."""
        config = dict(config or {})
        if config.get("deployment") and not config.get("model"):
            config["model"] = config["deployment"]
        super().initialize(config)
        self.deployment = config.get("deployment") or self.model
        self.api_version = config.get("api_version", self.DEFAULT_API_VERSION)

    def _path(self, endpoint: str) -> str:
        # Chat goes to the deployment; the model list is resource-wide.
        if endpoint == "/models":
            route = f"{self.api_prefix}/models"
        else:
            route = f"{self.api_prefix}/deployments/{self.deployment}{endpoint}"
        return f"{route}?api-version={self.api_version}"
