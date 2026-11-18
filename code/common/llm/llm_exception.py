"""Exceptions raised by LLM adapters."""


class LLMError(Exception):
    """Base class of all LLM adapter errors."""


class LLMNotInitializedError(LLMError):
    """A method was called before ``initialize()`` or after ``shutdown()``."""

    def __init__(self, adapter: str) -> None:
        super().__init__(f"{adapter} is not initialized - call initialize() first")


class LLMConfigurationError(LLMError):
    """The configuration passed to ``initialize()`` is incomplete or invalid."""


class LLMConnectionError(LLMError):
    """The model server could not be reached."""


class LLMRequestError(LLMError):
    """The model server rejected the request (non-2xx status)."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class LLMResponseError(LLMError):
    """The model server answered, but the answer is unusable (shape, empty)."""


class LLMDependencyError(LLMError):
    """An optional third-party SDK required by the adapter is not installed."""

    def __init__(self, adapter: str, package: str, extra: str = "") -> None:
        hint = f' (pip install "ai_platform[{extra}]")' if extra else ""
        super().__init__(
            f"{adapter} requires the '{package}' package{hint}: pip install {package}"
        )
        self.package = package
