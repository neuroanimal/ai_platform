"""Architecture rule: imports must respect doc/arch/DEPENDENCY_RULES.md.

Runs ``ai_platform.common.tool.validate_dependencies`` over the code tree.
Accepted exceptions would be listed in ``KNOWN_VIOLATIONS`` (none since the
orchestrators moved out of common). The test fails on any violation not in
that list, and on listed ones that no longer exist, so the list stays honest.
"""

import os
import re

from ai_platform.common.tool.validate_dependencies import find_violations

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# file -> imported module. Empty since 2026-11-19: the orchestrators that made
# common import backend were moved to backend/service_layer/macro/orchestration
# and their CLIs to backend/ui_layer/cli. Add an entry here only together with
# a decision to accept the debt.
KNOWN_VIOLATIONS: set = set()

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
