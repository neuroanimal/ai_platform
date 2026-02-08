import re
from typing import List, Any

class PathHandler:
    """
    Odpowiada za parsowanie, normalizacje i porównywanie sciezek parametrów.
    Obsluguje formaty: dot-notation, brackets [N], escaped strings, regex placeholders.
    """

    def __init__(self, config_mapping: dict):
        self.config = config_mapping
        # Regex do wylapywania segmentów:
        # 1. Tekst w cudzyslowie (obsluga escaped quotes)
        # 2. Tekst w nawiasach kwadratowych [N] lub [id="x"]
        # 3. Dynamiczne placeholdery {{...}}
        # 4. Standardowe klucze rozdzielone kropka
        self.token_regex = re.compile(
            r'\"(?P<quoted>.*?)(?<!\\)\"|'      # "quoted.segment"
            r'\[(?P<index>.*?)\]|'             # [0] lub [id="abc"]
            r'\{\{(?P<dynamic>.*?)\}\}|'       # {{placeholder}}
            r'(?P<plain>[^.\[\]{}"]+)'         # plain_key
        )

    def tokenize(self, path: str) -> List[dict]:
        """Rozbija surowa sciezke na liste tokenów z metadanymi."""
        tokens = []
        for match in self.token_regex.finditer(path):
            if match.group('quoted'):
                tokens.append({'type': 'key', 'value': match.group('quoted'), 'escaped': True})
            elif match.group('index'):
                val = match.group('index')
                t_type = 'array_index' if val.isdigit() else 'array_selector'
                tokens.append({'type': t_type, 'value': val})
            elif match.group('dynamic'):
                tokens.append({'type': 'dynamic', 'value': match.group('dynamic')})
            elif match.group('plain'):
                tokens.append({'type': 'key', 'value': match.group('plain'), 'escaped': False})
        return tokens

    def is_match(self, template_path: str, schema_path: str) -> bool:
        """
        Sprawdza czy sciezka z szablonu pasuje do sciezki z modelu (SSOT),
        uwzgledniajac placeholdery {{xyz}}.
        """
        t_tokens = self.tokenize(template_path)
        s_tokens = self.tokenize(schema_path)

        if len(t_tokens) != len(s_tokens):
            return False

        for t, s in zip(t_tokens, s_tokens):
            if t['type'] == 'dynamic' or s['type'] == 'dynamic':
                continue  # Akceptujemy dowolne dopasowanie dla placeholderów
            if t['value'] != s['value']:
                return False
        return True

    def get_depth(self, path: str) -> int:
        """Zwraca glebokosc zagniezdzenia (potrzebne do wyliczania spacji)."""
        return len(self.tokenize(path))
