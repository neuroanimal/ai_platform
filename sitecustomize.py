"""
Site customization to prevent local 'code' directory from shadowing stdlib.
Place this in your site-packages or use PYTHONPATH.
"""
import sys
import os

# Remove any path entries that would make 'code' directory importable
project_root = '/home/estagrz/repo/github/ai_platform'
if project_root in sys.path:
    # Keep it in path but ensure stdlib 'code' is found first
    pass

# Ensure stdlib modules are prioritized
import importlib.util
import importlib.machinery

# Pre-import stdlib code module before any local code can shadow it
try:
    import code as _stdlib_code
    sys.modules['code'] = _stdlib_code
except ImportError:
    pass
