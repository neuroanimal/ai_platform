"""
Tools an LLM may call, and their registry.

A tool is a name, a description (what the model reads to decide whether to
use it), a JSON Schema for its arguments and a Python function. Arguments
proposed by the model are validated against the schema *before* the function
runs; a validation error or an exception inside the tool becomes a
``ToolResult`` with ``ok=False`` that is shown to the model, so the loop can
continue (the model may correct itself) instead of crashing.

``side_effects`` marks tools that change something outside the process
(write a file, send a request that mutates state). The agent refuses to run
them unless explicitly allowed.

The validator covers the JSON Schema subset tool definitions use: type,
properties, required, enum, items, minimum/maximum, additionalProperties.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
          "object": dict, "array": list, "null": type(None)}


class ToolError(Exception):
    """Invalid tool definition or registration."""


def validate_arguments(value: Any, schema: Dict[str, Any],  # pylint: disable=too-many-branches
                       path: str = "$") -> List[str]:
    """Problems of ``value`` against ``schema`` (empty list = valid)."""
    problems: List[str] = []
    expected = schema.get("type")
    if expected:
        types = expected if isinstance(expected, list) else [expected]
        python_types = tuple(t for name in types for t in
                             (_TYPES[name] if isinstance(_TYPES[name], tuple) else (_TYPES[name],)))
        is_bool = isinstance(value, bool)
        if not isinstance(value, python_types) or (is_bool and "boolean" not in types):
            return [f"{path}: expected {expected}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            problems.append(f"{path}: {value} > maximum {schema['maximum']}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                problems.append(f"{path}: missing required '{name}'")
        for name, item in value.items():
            if name in properties:
                problems.extend(validate_arguments(item, properties[name], f"{path}.{name}"))
            elif schema.get("additionalProperties") is False:
                problems.append(f"{path}: unexpected property '{name}'")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            problems.extend(validate_arguments(item, schema["items"], f"{path}[{index}]"))
    return problems


@dataclass
class ToolResult:
    """Outcome of one tool call, as shown to the model."""

    ok: bool
    content: Any
    error: Optional[str] = None

    def to_text(self) -> str:
        """Text for the ``role: tool`` message."""
        if not self.ok:
            return json.dumps({"error": self.error}, ensure_ascii=False)
        if isinstance(self.content, str):
            return self.content
        return json.dumps(self.content, ensure_ascii=False, default=str)


@dataclass
class Tool:
    """One callable tool."""

    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable[..., Any]
    side_effects: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.replace("_", "").replace("-", "").isalnum():
            raise ToolError(f"tool name {self.name!r}: letters, digits, '_' and '-' only")
        if self.parameters.get("type") != "object":
            raise ToolError(f"tool {self.name}: parameters schema must be of type object")

    def schema(self) -> Dict[str, Any]:
        """OpenAI function-tool definition."""
        return {"type": "function", "function": {"name": self.name,
                                                 "description": self.description,
                                                 "parameters": self.parameters}}

    def call(self, arguments: Dict[str, Any]) -> ToolResult:
        """Validate and run; never raises for bad arguments or tool failures."""
        problems = validate_arguments(arguments, self.parameters)
        if problems:
            return ToolResult(False, None, "invalid arguments: " + "; ".join(problems))
        try:
            return ToolResult(True, self.function(**arguments))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return ToolResult(False, None, f"{type(exc).__name__}: {exc}")


class ToolRegistry:
    """Explicitly registered tools (no discovery)."""

    def __init__(self, tools: Optional[List[Tool]] = None) -> None:
        self._tools: Dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """Add a tool; names are unique."""
        if tool.name in self._tools:
            raise ToolError(f"tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Tool by name, or None."""
        return self._tools.get(name)

    def names(self) -> List[str]:
        """Registered names."""
        return list(self._tools)

    def schemas(self) -> List[Dict[str, Any]]:
        """OpenAI tool definitions of all tools."""
        return [tool.schema() for tool in self._tools.values()]
