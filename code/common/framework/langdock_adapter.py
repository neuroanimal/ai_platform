"""Langdock adapter (Langdock's OpenAI-compatible completion API).

Langdock is a hosted enterprise AI workspace. Its API offers an
OpenAI-compatible chat completions endpoint, so this adapter is a thin
use of ``OpenAICompatibleAdapter``:

    base_url   default "https://api.langdock.com/openai/eu" (region in the path)
    model      model name as enabled in your workspace (required)
    api_key / api_key_env   default env LANGDOCK_API_KEY

``execute({"input": "prompt" | [messages]})`` returns the answer text as
``output`` and the ``ChatResult`` as ``raw``.

Based on Langdock's published API description; not verified against the
service here (no key). Previously a stub echoing the task; the class name
and the FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import FrameworkBase, FrameworkError, task_input
from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class _LangdockLLM(OpenAICompatibleAdapter):
    """OpenAI-compatible defaults for Langdock."""

    PROVIDER = "langdock"
    DEFAULT_BASE_URL = "https://api.langdock.com/openai/eu"
    DEFAULT_API_KEY_ENV = "LANGDOCK_API_KEY"
    REQUIRES_API_KEY = True


class LangDockAdapter(FrameworkBase):
    """Chat completions through Langdock."""

    FRAMEWORK = "Langdock"

    def __init__(self):
        super().__init__()
        self.llm = None

    def _setup(self, config: Dict[str, Any]) -> None:
        self.llm = _LangdockLLM()
        try:
            self.llm.initialize(config)
        except LLMError as exc:
            raise FrameworkError(str(exc)) from exc

    def _run(self, task: Dict[str, Any]):
        value = task_input(task)
        messages = value if isinstance(value, list) else [{"role": "user", "content": str(value)}]
        try:
            result = self.llm.chat_completion(messages)
        except LLMError as exc:
            raise FrameworkError(str(exc)) from exc
        return result.text, result
