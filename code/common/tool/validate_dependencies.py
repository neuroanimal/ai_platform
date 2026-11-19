"""
Dependency Validator for ai-platform

Checks that Python imports respect the layer boundaries defined
in doc/arch/DEPENDENCY_RULES.md.

Rules are hard-coded for now based on architecture document.

How it decides (rewritten 2026-11-19; the first version compared dotted
module names with slash-separated directories, so it flagged every import,
standard library included, and could not find a real violation):

- only *platform-internal* imports are checked: ``ai_platform.<area>...``
  (the installed package name) and the legacy spellings ``code.<area>``,
  ``common.<area>``, ``backend.<area>``. Standard-library and third-party
  imports are outside the scope of these rules;
- imports anywhere in the file count, including lazy imports inside
  functions;
- a file belongs to the most specific layer in ``LAYER_RULES``; it may
  import its own layer and the layers listed for it.

Run from the repository root: ``python -m ai_platform.common.tool.validate_dependencies``
(exit status 1 when violations exist).
"""

import ast
import os
import sys
from typing import Dict, List, Optional

# Mapping: directory -> allowed import roots (besides its own directory)
LAYER_RULES: Dict[str, List[str]] = {
    "code/common": [],
    "code/common/example": ["code/common"],
    "code/backend/data_layer": ["code/common"],
    "code/backend/domain_layer": ["code/common", "code/backend/data_layer"],
    "code/backend/service_layer": ["code/common", "code/backend/domain_layer"],
    "code/backend/ui_layer": ["code/common", "code/backend/service_layer"],
    "code/frontend": ["code/common"],
}

# Directories to scan for Python files
SCAN_DIRS = [
    "code/common",
    "code/backend",
    "code/frontend",
]

# Spellings of a platform-internal module, mapped to its directory prefix.
_INTERNAL_PREFIXES = {
    "ai_platform.": "code/",
    "code.": "code/",
    "common.": "code/common/",
    "backend.": "code/backend/",
    "frontend.": "code/frontend/",
}


def module_directory(import_name: str) -> Optional[str]:
    """Directory of a platform-internal module, or None for external modules."""
    for prefix, directory in _INTERNAL_PREFIXES.items():
        if import_name.startswith(prefix):
            return directory + import_name[len(prefix):].replace(".", "/")
    return None


def layer_of(file_path: str) -> Optional[str]:
    """Most specific layer directory containing ``file_path``."""
    normalized = file_path.replace(os.sep, "/")
    matches = [layer for layer in LAYER_RULES
               if normalized == layer or normalized.startswith(layer + "/")]
    return max(matches, key=len) if matches else None


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def is_import_allowed(file_path, import_name):
    """
    Check if import_name is allowed based on LAYER_RULES.
    import_name is absolute import like 'ai_platform.common.core.registry.plugin_registry'
    """
    target = module_directory(import_name)
    if target is None:
        return True  # standard library / third party: not a layer question
    layer = layer_of(file_path)
    if layer is None:
        return True  # file is outside defined layers, allow by default
    allowed = [layer, *LAYER_RULES[layer]]
    return any(_within(target, root) for root in allowed)


def scan_file(file_path):
    """
    Parse Python file and check imports (top-level and nested)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        node = ast.parse(f.read(), filename=file_path)

    violations = []

    for stmt in ast.walk(node):
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if not is_import_allowed(file_path, alias.name):
                    violations.append(f"{file_path}:{stmt.lineno}: import {alias.name} not allowed")
        elif isinstance(stmt, ast.ImportFrom):
            module = stmt.module
            if stmt.level == 0 and module and not is_import_allowed(file_path, module):
                violations.append(
                    f"{file_path}:{stmt.lineno}: from {module} import ... not allowed")
    return violations


def scan_directory(directory):
    """All violations under ``directory``."""
    violations = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fname in sorted(files):
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                violations.extend(scan_file(fpath))
    return violations


def find_violations(base_dir: str = ".") -> List[str]:
    """Violations in SCAN_DIRS, relative to ``base_dir``."""
    previous = os.getcwd()
    os.chdir(base_dir)
    try:
        found = []
        for d in SCAN_DIRS:
            if os.path.exists(d):
                found.extend(scan_directory(d))
            else:
                print(f"Directory not found: {d}")
        return found
    finally:
        os.chdir(previous)


def main():
    """Print violations; exit 1 when there are any."""
    all_violations = find_violations()

    if all_violations:
        print("Dependency violations found:")
        for v in all_violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("All imports respect layer boundaries.")


if __name__ == "__main__":
    main()
