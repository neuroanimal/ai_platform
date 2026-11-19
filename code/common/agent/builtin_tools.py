"""
Built-in tools without side effects.

- ``calculator``: arithmetic on numbers with + - * / // % ** and parentheses,
  evaluated by walking the Python AST (no ``eval``), with limits on exponent
  and result size so a model cannot make the process compute forever;
- ``convert_units``: length, mass, time and temperature conversions;
- ``current_date``: today's date (local time zone);
- ``rag_search_tool(rag)``: search in a platform RAG index (``NativeRAGAdapter``
  or any object with ``retrieve(question, top_k)``).
"""

import ast
import datetime
import math
import operator
from typing import Any, Dict

from ai_platform.common.agent.tool import Tool

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
           ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MAX_EXPONENT = 100
MAX_MAGNITUDE = 1e100


def safe_arithmetic(expression: str) -> float:
    """Value of an arithmetic expression (numbers and operators only)."""
    text = str(expression).replace("×", "*").replace("÷", "/").replace("^", "**")
    text = text.replace(",", ".") if text.count(",") and "." not in text else text

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
                raise ValueError(f"exponent {right} too large")
            value = _BINARY[type(node.op)](left, right)
            if abs(value) > MAX_MAGNITUDE:
                raise ValueError("result too large")
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](walk(node.operand))
        raise ValueError(f"not allowed in an arithmetic expression: {type(node).__name__}")

    value = walk(ast.parse(text.strip(), mode="eval"))
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _calculator(expression: str) -> Dict[str, Any]:
    return {"expression": expression, "result": safe_arithmetic(expression)}


CALCULATOR = Tool(
    name="calculator",
    description="Evaluate an arithmetic expression exactly, e.g. '17 * 23 * 19' or "
                "'(112 - 100) / 100 * 100'. Use it for any calculation.",
    parameters={"type": "object", "properties": {
        "expression": {"type": "string", "description": "arithmetic expression"}},
        "required": ["expression"], "additionalProperties": False},
    function=_calculator)

_FACTORS = {  # unit -> (dimension, factor to the base unit)
    "mm": ("length", 0.001), "cm": ("length", 0.01), "m": ("length", 1.0),
    "km": ("length", 1000.0), "in": ("length", 0.0254), "ft": ("length", 0.3048),
    "mi": ("length", 1609.344), "g": ("mass", 0.001), "kg": ("mass", 1.0),
    "t": ("mass", 1000.0), "lb": ("mass", 0.45359237), "s": ("time", 1.0),
    "min": ("time", 60.0), "h": ("time", 3600.0), "day": ("time", 86400.0),
}
_TEMPERATURE = ("c", "f", "k")


def _convert(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    source, target = from_unit.strip().lower(), to_unit.strip().lower()
    if source in _TEMPERATURE and target in _TEMPERATURE:
        kelvin = {"c": value + 273.15, "f": (value - 32) * 5 / 9 + 273.15, "k": value}[source]
        result = {"c": kelvin - 273.15, "f": (kelvin - 273.15) * 9 / 5 + 32, "k": kelvin}[target]
    else:
        if source not in _FACTORS or target not in _FACTORS:
            raise ValueError(f"unknown unit; known: {sorted(_FACTORS) + list(_TEMPERATURE)}")
        if _FACTORS[source][0] != _FACTORS[target][0]:
            raise ValueError(f"cannot convert {_FACTORS[source][0]} to {_FACTORS[target][0]}")
        result = value * _FACTORS[source][1] / _FACTORS[target][1]
    result = round(result, 10)
    return {"value": value, "from": from_unit, "to": to_unit,
            "result": int(result) if math.isclose(result, round(result)) else result}


UNIT_CONVERTER = Tool(
    name="convert_units",
    description="Convert a value between units of length (mm, cm, m, km, in, ft, mi), mass "
                "(g, kg, t, lb), time (s, min, h, day) or temperature (C, F, K).",
    parameters={"type": "object", "properties": {
        "value": {"type": "number"}, "from_unit": {"type": "string"},
        "to_unit": {"type": "string"}},
        "required": ["value", "from_unit", "to_unit"], "additionalProperties": False},
    function=_convert)

CURRENT_DATE = Tool(
    name="current_date",
    description="Today's date as YYYY-MM-DD with the weekday.",
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    function=lambda: {"date": datetime.date.today().isoformat(),
                      "weekday": datetime.date.today().strftime("%A")})


def rag_search_tool(rag, name: str = "search_documents", top_k: int = 3,
                    description: str = "Search the document collection and return the most "
                                       "relevant passages. Use it for questions about facts "
                                       "you do not know.") -> Tool:
    """A tool that searches ``rag`` (anything with ``retrieve(question, top_k)``)."""
    def search(query: str):
        return [{"document_id": hit.get("document_id"), "text": hit.get("text"),
                 "score": round(float(hit.get("score") or 0.0), 3)}
                for hit in rag.retrieve(query, top_k)]
    return Tool(name=name, description=description, function=search,
                parameters={"type": "object", "properties": {
                    "query": {"type": "string", "description": "what to look for"}},
                    "required": ["query"], "additionalProperties": False})


def default_tools():
    """Calculator, unit converter and date - all without side effects."""
    return [CALCULATOR, UNIT_CONVERTER, CURRENT_DATE]
