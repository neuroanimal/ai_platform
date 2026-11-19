"""Priority-based prompt assembly under a token budget.

Priompt (Anysphere) is a TypeScript/JSX library and has no Python package,
so this adapter is a Python implementation of the same idea rather than a
binding: every part of the prompt has a priority, and when the rendered
prompt exceeds the token budget the lowest-priority parts are dropped first.

``render(template, variables)``:

- ``template`` uses ``{name}`` placeholders (``str.format`` syntax);
- each variable is either plain text (never dropped) or a *scope*::

      {"text": "...", "priority": 10}            # one droppable part
      [{"text": "...", "priority": 5}, ...]      # list: parts joined by "\n"

  Higher priority = kept longer. Within one list, parts are dropped
  individually, so a long history loses its oldest (lowest-priority) turns.

Configuration:

    token_budget    default 4096
    count_tokens    callable(str) -> int; default: ceil(len(text) / 4), a
                    rough estimate - pass a real tokenizer for exact budgets

If the prompt still exceeds the budget with every droppable part removed,
``PromptError`` is raised. ``last_dropped`` lists what was removed.

Previously a stub returning a fabricated string; the class name and the
PromptAdapter methods are unchanged.
"""

import math
from typing import Any, Callable, Dict, List

from ai_platform.common.prompt.base import PromptAdapter
from ai_platform.common.prompt.jinja2_prompt_adapter import PromptError


def estimate_tokens(text: str) -> int:
    """About four characters per token - a deliberately rough default."""
    return math.ceil(len(text) / 4)


class PriomptAdapter(PromptAdapter):
    """Drops lowest-priority prompt parts until the prompt fits the budget."""

    def __init__(self):
        self.initialized = False
        self.priority_queue: List[Dict[str, Any]] = []
        self.token_budget = 0
        self.count_tokens: Callable[[str], int] = estimate_tokens
        self.last_dropped: List[Dict[str, Any]] = []

    def initialize(self, config: Dict[str, Any]) -> None:
        """Read the budget and the token counter."""
        config = dict(config or {})
        self.token_budget = int(config.get("token_budget", 4096))
        self.count_tokens = config.get("count_tokens", estimate_tokens)
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Render, dropping parts by ascending priority until within budget."""
        if not self.initialized:
            raise PromptError("PriomptAdapter is not initialized")
        parts = self._parts(variables or {})
        # Candidates for removal: (priority, order) - lowest priority first,
        # and among equals the earliest part (e.g. the oldest history turn).
        removable = sorted(((p["priority"], i) for i, p in enumerate(parts)
                            if p["priority"] is not None))
        self.last_dropped = []
        text = self._fill(template, variables or {}, parts)
        while self.count_tokens(text) > self.token_budget and removable:
            _, index = removable.pop(0)
            parts[index]["kept"] = False
            self.last_dropped.append({"variable": parts[index]["variable"],
                                      "priority": parts[index]["priority"],
                                      "text": parts[index]["text"]})
            text = self._fill(template, variables or {}, parts)
        if self.count_tokens(text) > self.token_budget:
            raise PromptError(
                f"prompt needs {self.count_tokens(text)} tokens with all droppable parts "
                f"removed; budget is {self.token_budget}")
        self.priority_queue = [{"variable": p["variable"], "priority": p["priority"],
                                "kept": p["kept"]} for p in parts]
        return text

    def shutdown(self) -> None:
        """Reset state."""
        self.initialized = False
        self.priority_queue.clear()
        self.last_dropped = []
        self.token_budget = 0

    @staticmethod
    def _parts(variables: Dict[str, Any]) -> List[Dict[str, Any]]:
        parts = []
        for name, value in variables.items():
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, dict) and "text" in item:
                    parts.append({"variable": name, "text": str(item["text"]),
                                  "priority": item.get("priority", 0), "kept": True})
                else:
                    parts.append({"variable": name, "text": str(item),
                                  "priority": None, "kept": True})
        return parts

    @staticmethod
    def _fill(template: str, variables: Dict[str, Any], parts: List[Dict[str, Any]]) -> str:
        values: Dict[str, List[str]] = {name: [] for name in variables}
        for part in parts:
            if part["kept"]:
                values[part["variable"]].append(part["text"])
        try:
            return template.format(**{k: "\n".join(v) for k, v in values.items()})
        except KeyError as exc:
            raise PromptError(f"priompt: missing variable {exc}") from exc
