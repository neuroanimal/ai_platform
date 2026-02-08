from yamllint import linter
from yamllint.config import YamlLintConfig

class TemplateValidator:
    """YAML validation using yamllint."""

    def __init__(self, tracer, config_str: str = None):
        self.tracer = tracer
        self.stats = {"errors": 0, "warnings": 0}

        if config_str:
            self.lint_config = YamlLintConfig(config_str)
        else:
            self.lint_config = YamlLintConfig(
                'extends: relaxed\n'
                'rules:\n'
                '  indentation: {level: error}\n'
                '  line-length: disable'
            )

    def validate(self, content: str) -> list:
        """Run yamllint and return issues."""
        self.tracer.info("Running yamllint validation")
        issues = []
        self.stats = {"errors": 0, "warnings": 0}

        try:
            for problem in linter.run(content, self.lint_config):
                issue = {
                    "line": problem.line,
                    "column": problem.column,
                    "level": problem.level,
                    "message": problem.message,
                    "rule": problem.rule
                }
                issues.append(issue)

                if problem.level == "error":
                    self.stats["errors"] += 1
                else:
                    self.stats["warnings"] += 1

                self.tracer.debug(f"[{problem.level.upper()}] Line {problem.line}: {problem.message}")

            if self.stats["errors"] > 0:
                self.tracer.warning(f"Found {self.stats['errors']} errors")
            else:
                self.tracer.info("No critical errors found")

            return issues
        except Exception as e:
            self.tracer.error(f"Validation failed: {e}")
            return []

    def get_summary(self) -> dict:
        return self.stats
