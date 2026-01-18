"""
White-box test: validate architecture rules
Runs the dependency validator from common/tool.
"""

import unittest
from code.common.tool.validate_dependencies import main as validate_main

class TestArchitectureRules(unittest.TestCase):
    def test_dependencies(self):
        """
        Run the dependency validator. Fails if any import violates rules.
        """
        try:
            validate_main()
        except SystemExit as e:
            if e.code != 0:
                self.fail("Dependency validator detected violations.")

if __name__ == "__main__":
    unittest.main()
