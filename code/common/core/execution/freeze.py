"""
Deep freezing for the contract's "immutable" data (labels, metadata extras, error details).

``frozen=True`` on a dataclass only stops re-assigning its fields; a dict
inside can still be changed. ``deep_freeze`` turns nested data into
read-only equivalents: mappings into ``MappingProxyType`` (of frozen
values), lists and tuples into tuples, sets into frozensets. Scalars (str,
int, float, bool, None) stay as they are; any other object is normalized to
its ``str`` - labels and metadata are data, not live objects. ``thaw``
converts back to plain dict/list for JSON.
"""

from types import MappingProxyType
from typing import Any, Mapping

_SCALARS = (str, int, float, bool, type(None))


def deep_freeze(value: Any) -> Any:
    """Read-only copy of ``value`` (see the module docstring)."""
    if isinstance(value, _SCALARS):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): deep_freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(deep_freeze(v) for v in value)
    return str(value)


def thaw(value: Any) -> Any:
    """Plain, JSON-compatible copy of frozen data."""
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [thaw(v) for v in value]
    if isinstance(value, frozenset):
        return sorted((thaw(v) for v in value), key=repr)
    return value
