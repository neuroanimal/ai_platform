"""
Shared base of the agent/orchestration framework adapters.

These frameworks are libraries whose central object (a crew, a graph, an
agent, a kernel function, a pipeline) is built with the framework's own,
rich API - re-describing all of that as a generic config dict would be a
second, worse API. So each adapter takes the framework's object, already
built, in ``initialize(config)``, and ``execute(task)`` runs it and returns
a uniform result::

    {"framework": "<name>", "output": <main textual/structured output>, "raw": <native result>}

``task`` is ``{"input": <str or dict>}`` plus adapter-specific keys. Some
adapters can also build a minimal object from a platform LLM adapter
(``llm``) for the simple "prompt in, answer out" case; each documents it.

Imports of the framework are lazy: a missing package raises
``FrameworkError`` naming it.
"""

import asyncio
import importlib
from typing import Any, Dict

from ai_platform.common.framework.base import FrameworkAdapter


class FrameworkError(Exception):
    """Framework adapter misuse, missing package or failed run."""


def require_module(name: str, package: str):
    """Import ``name`` or raise FrameworkError telling which package to install."""
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise FrameworkError(f"requires: pip install {package}") from exc


def run_sync(value):
    """Await ``value`` if it is awaitable (frameworks with async APIs)."""
    if asyncio.iscoroutine(value):
        return asyncio.run(value)
    return value


def task_input(task: Dict[str, Any]) -> Any:
    """The task's ``input`` (required)."""
    if not isinstance(task, dict) or "input" not in task:
        raise FrameworkError("task needs an 'input'")
    return task["input"]


class FrameworkBase(FrameworkAdapter):
    """Lifecycle shared by the framework adapters."""

    FRAMEWORK = "framework"

    def __init__(self):
        self.initialized = False
        self.config: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Keep the configuration; ``_setup`` validates/builds the native object."""
        self.config = dict(config or {})
        self._setup(self.config)
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run the native object on ``task``."""
        if not self.initialized:
            raise FrameworkError(f"{type(self).__name__} is not initialized")
        output, raw = self._run(task)
        return {"framework": self.FRAMEWORK, "output": output, "raw": raw}

    def shutdown(self) -> None:
        """Drop references to the native objects."""
        self.config = {}
        self.initialized = False

    def _setup(self, config: Dict[str, Any]) -> None:
        """Validate configuration / build the native object."""

    def _run(self, task: Dict[str, Any]):
        """Return (output, raw)."""
        raise NotImplementedError

    def _needs(self, key: str, what: str) -> Any:
        """A required config entry."""
        if self.config.get(key) is None:
            raise FrameworkError(f"{type(self).__name__} needs config[{key!r}]: {what}")
        return self.config[key]
