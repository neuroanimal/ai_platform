"""Architecture rule: imports must respect doc/arch/DEPENDENCY_RULES.md.

Runs ``ai_platform.common.tool.validate_dependencies`` over the code tree.
Violations that existed before the validator worked are listed in
``KNOWN_VIOLATIONS`` - they are architecture debt to remove (each needs a
refactoring decision, e.g. moving the orchestrators from common/engine into
backend), not accepted design. The test fails on any *new* violation and
also when a known one disappears, so the list is kept honest.
"""

import os
import re

from ai_platform.common.tool.validate_dependencies import find_violations

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# file -> imported module; common must not import backend.
KNOWN_VIOLATIONS = {
    ("code/common/engine/unified_orchestrator_engine.py",
     "ai_platform.backend.service_layer.format_processing.yaml.yaml_processing_service"),
    ("code/common/engine/unified_orchestrator_engine.py",
     "ai_platform.backend.service_layer.schema_processing.jsonschema_processing_service"),
    ("code/common/engine/unified_processing_engine.py",
     "ai_platform.backend.service_layer.yaml_processing.yaml_processing_service"),
    ("code/common/engine/unified_processing_engine.py",
     "ai_platform.backend.service_layer.schema_processing.jsonschema_processing_service"),
    ("code/common/tool/enhanced_unified_cli.py",
     "ai_platform.backend.service_layer.format_processing.conversion.format_conversion_service"),
}

LINE = re.compile(r"^(?P<file>[^:]+):\d+: (?:from (?P<a>\S+) import \.\.\.|import (?P<b>\S+)) not allowed$")


def parse(violation):
    """(file, module) of one validator message."""
    match = LINE.match(violation)
    assert match, violation
    return match.group("file"), match.group("a") or match.group("b")


def test_no_new_layer_violations():
    found = {parse(v) for v in find_violations(ROOT)}
    assert found - KNOWN_VIOLATIONS == set(), "new layer violations"
    assert KNOWN_VIOLATIONS - found == set(), "fixed violations: remove them from KNOWN_VIOLATIONS"


def test_validator_detects_a_violation(tmp_path):
    from ai_platform.common.tool.validate_dependencies import (  # pylint: disable=import-outside-toplevel
        is_import_allowed,
    )
    assert not is_import_allowed("code/common/x.py", "ai_platform.backend.service_layer.y")
    assert not is_import_allowed("code/backend/ui_layer/cli/x.py",
                                 "ai_platform.backend.domain_layer.z")
    assert is_import_allowed("code/backend/ui_layer/cli/x.py", "ai_platform.backend.service_layer.z")
    assert is_import_allowed("code/common/x.py", "json")
    assert is_import_allowed("code/common/example/x.py", "ai_platform.common.llm.base")
    del tmp_path
