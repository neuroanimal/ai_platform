#!/usr/bin/env python3
"""Test if pydantic works with cross-version binaries"""

import sys

print(f"Python version: {sys.version}")

try:
    import pydantic  # type: ignore[import-not-found]

    print(f"✓ pydantic imported: {pydantic.__version__}")

    from pydantic import BaseModel  # type: ignore[import-not-found]

    print("✓ BaseModel imported")

    class TestModel(BaseModel):  # pylint: disable=too-few-public-methods
        """Test model for pydantic validation."""

        name: str
        age: int

    print("✓ Model defined")

    obj = TestModel(name="test", age=42)
    print(f"✓ Model instantiated: {obj}")

    print("\n✅ SUCCESS - pydantic works!")

except (ImportError, AttributeError, TypeError, ValueError) as e:
    print(f"\n❌ FAILED: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
