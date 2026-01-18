"""
Dependency Validator for ai-platform

Checks that Python imports respect the layer boundaries defined
in doc/arch/DEPENDENCY_RULES.md.

Rules are hard-coded for now based on architecture document.
"""

import os
import ast

# Mapping: directory -> allowed import roots
LAYER_RULES = {
    "code/common": ["code/common"],
    "code/backend/data_layer": ["code/common"],
    "code/backend/domain_layer": ["code/common", "code/backend/data_layer"],
    "code/backend/service_layer": ["code/common", "code/backend/domain_layer"],
    "code/backend/ui_layer": ["code/common", "code/backend/service_layer"],
    "code/frontend": ["code/common"],
    "code/common/example": ["code/common/core", "code/common/engine", "code/common/util"],
}

# Directories to scan for Python files
SCAN_DIRS = [
    "code/common",
    "code/backend",
    "code/frontend",
]

def is_import_allowed(file_path, import_name):
    """
    Check if import_name is allowed based on LAYER_RULES.
    import_name is absolute import like 'code.common.core.registry.plugin_registry'
    """
    # Determine the layer of the file
    for layer_path, allowed_roots in LAYER_RULES.items():
        if os.path.commonpath([file_path, layer_path]) == layer_path:
            # file belongs to this layer
            # check if import_name starts with any allowed root
            for allowed in allowed_roots:
                if import_name.startswith(allowed):
                    return True
            return False
    # File is outside defined layers, allow by default
    return True

def scan_file(file_path):
    """
    Parse Python file and check imports
    """
    with open(file_path, "r", encoding="utf-8") as f:
        node = ast.parse(f.read(), filename=file_path)

    violations = []

    for stmt in node.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if not is_import_allowed(file_path, alias.name):
                    violations.append(f"{file_path}: import {alias.name} not allowed")
        elif isinstance(stmt, ast.ImportFrom):
            module = stmt.module
            if module and not is_import_allowed(file_path, module):
                violations.append(f"{file_path}: from {module} import ... not allowed")
    return violations

def scan_directory(directory):
    violations = []
    for root, dirs, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                violations.extend(scan_file(fpath))
    return violations

def main():
    all_violations = []
    for d in SCAN_DIRS:
        if os.path.exists(d):
            all_violations.extend(scan_directory(d))
        else:
            print(f"Directory not found: {d}")

    if all_violations:
        print("Dependency violations found:")
        for v in all_violations:
            print(f"  {v}")
        exit(1)
    else:
        print("All imports respect layer boundaries.")

if __name__ == "__main__":
    main()
