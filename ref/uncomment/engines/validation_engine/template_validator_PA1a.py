import os
from yamllint import linter
from yamllint.config import YamlLintConfig
from common.trace_handler import TraceHandler
from common.error_handler import ValidationError

class TemplateValidator:
    """
    Modul walidacji szablonu wyjsciowego.
    Wykorzystuje yamllint do wykrywania bledów strukturalnych i stylistycznych.
    """
    def __init__(self, tracer: TraceHandler, config_path: str = None):
        self.tracer = tracer
        self.stats = {"errors": 0, "warnings": 0}

        # Konfiguracja lintera - jesli nie ma pliku, uzywamy domyslnej "relaxed"
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.lint_config = YamlLintConfig(f.read())
        else:
            # Domyslna konfiguracja dopuszczajaca dlugie linie, ale rygorystyczna dla wciec
            self.lint_config = YamlLintConfig('extends: relaxed\nrules:\n  indentation: {level: error}\n  line-length: disable')

    def validate(self, file_path: str) -> list:
        """
        Uruchamia proces lintowania na wskazanym pliku.
        Zwraca liste obiektów bledów przygotowana dla AI Fixera.
        """
        self.tracer.info(f"Uruchamianie walidacji linterem dla: {file_path}")
        issues = []
        self.stats = {"errors": 0, "warnings": 0}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Uruchomienie yamllint
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

                self.tracer.debug(f"Linter Found [{problem.level.upper()}]: Line {problem.line} - {problem.message}")

            if self.stats["errors"] > 0:
                self.tracer.warning(f"Linter wykryl {self.stats['errors']} krytycznych bledów strukturalnych.")
            else:
                self.tracer.info("Linter nie znalazl krytycznych bledów strukturalnych.")

            return issues

        except Exception as e:
            self.tracer.logger.error(f"Krytyczny blad podczas pracy lintera: {str(e)}")
            return []

    def get_summary(self) -> dict:
        return self.stats

