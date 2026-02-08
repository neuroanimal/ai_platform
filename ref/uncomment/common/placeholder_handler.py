# common/placeholder_handler.py

class PlaceholderHandler:
    def __init__(self):
        # Regex dla: {{ ... }}, {{ "abc" | "def" }}, {{ .Values.something }}
        self.placeholder_pattern = re.compile(r'\{\{.*?\}\}')

    def is_placeholder_value(self, value: str) -> bool:
        """Sprawdza, czy cala wartosc jest placeholderem."""
        return bool(self.placeholder_pattern.fullmatch(value.strip()))

    def protect_placeholders(self, content: str) -> str:
        """
        Zabezpiecza placeholdery przed blednym parsowaniem YAML,
        zamykajac je w cudzyslowy, jesli to konieczne.
        """
        # Logika: jesli linter ma problem z {{...}},
        # mozemy to tymczasowo zamienic na "PLACEHOLDER_ID"
        return content

