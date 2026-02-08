import re
from typing import List, Any

class PathHandler:
    """
    Odpowiada za parsowanie, normalizacje i porównywanie sciezek parametrów.
    Obsluguje formaty: dot-notation, brackets [N], escaped strings, regex placeholders.
    """

    def __init__(self):
    ### def __init__(self, config_mapping: dict):
        ### self.config = config_mapping
        # Regex do wylapywania segmentów:
        # 1. Tekst w cudzyslowie (obsluga escaped quotes)
        # 2. Tekst w nawiasach kwadratowych [N] lub [id="x"]
        # 3. Dynamiczne placeholdery {{...}}
        # 4. Standardowe klucze rozdzielone kropka
        # Regex obslugujacy: "quoted", [index], {{dynamic}}, plain_key
        self.token_regex = re.compile(
            r'\"(?P<quoted>.*?)(?<!\\)\"|'
            r'\[(?P<index>.*?)\]|'
            r'\{\{(?P<dynamic>.*?)\}\}|'
            r'(?P<plain>[^.\[\]{}"]+)'
        )

    def tokenize(self, path: str) -> List[dict]:
        """Rozbija surowa sciezke na liste tokenów z metadanymi."""

        if not path: return []
        # Normalizacja separatorów przed tokenizacja (np. zamiana / na .)
        path = path.replace('\\', '.').replace('/', '.')

        tokens = []
        for match in self.token_regex.finditer(path):
            if match.group('quoted'):
                tokens.append({'type': 'key', 'value': match.group('quoted'), 'escaped': True})
            elif match.group('index'):
                val = match.group('index')
                # tokens.append({'type': 'index', 'value': val})
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

    def join_tokens(self, tokens: List[dict]) -> str:
        """Rekonstruuje sciezke z tokenów do formatu kanonicznego."""
        parts = []
        for t in tokens:
            if t['type'] == 'key':
                parts.append(f'"{t["value"]}"' if t['escaped'] else t['value'])
            elif t['type'] == 'index':
                parts[-1] = f"{parts[-1]}[{t['value']}]"
            elif t['type'] == 'dynamic':
                parts.append(f"{{{{{t['value']}}}}}")
        return ".".join(parts).replace(".[", "[")

