
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Recursive immutable containers for NLP provider configuration."""

from __future__ import annotations

from typing import Any


class FrozenDict(dict):
    """A dict-compatible mapping that rejects ordinary mutation operations."""

    def __init__(self, source: dict[str, Any] | None = None, **kwargs: Any) -> None:
        dict.__init__(self)

        if source is not None:
            for key, value in source.items():
                dict.__setitem__(self, key, deep_freeze(value))

        for key, value in kwargs.items():
            dict.__setitem__(self, key, deep_freeze(value))

    @staticmethod
    def _immutable(*args: Any, **kwargs: Any) -> None:
        raise TypeError("FrozenDict does not support mutation")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


def deep_freeze(value: Any) -> Any:
    """Recursively convert mutable dictionaries and lists to immutable forms."""

    if isinstance(value, FrozenDict):
        return value

    if isinstance(value, dict):
        return FrozenDict(value)

    if isinstance(value, list):
        return tuple(deep_freeze(item) for item in value)

    if isinstance(value, tuple):
        return tuple(deep_freeze(item) for item in value)

    if isinstance(value, set):
        return frozenset(deep_freeze(item) for item in value)

    return value


def deep_thaw(value: Any) -> Any:
    """Convert immutable containers back to JSON-compatible mutable containers."""

    if isinstance(value, dict):
        return {
            key: deep_thaw(item)
            for key, item in value.items()
        }

    if isinstance(value, (tuple, list)):
        return [deep_thaw(item) for item in value]

    if isinstance(value, (set, frozenset)):
        return [deep_thaw(item) for item in value]

    return value


