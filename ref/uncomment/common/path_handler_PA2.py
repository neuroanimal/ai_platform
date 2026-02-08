import re
from typing import List

class PathHandler:
    def __init__(self):
        # Regex obslugujacy: "quoted", [index], {{dynamic}}, plain_key
        self.token_regex = re.compile(
            r'\"(?P<quoted>.*?)(?<!\\)\"|'
            r'\[(?P<index>.*?)\]|'
            r'\{\{(?P<dynamic>.*?)\}\}|'
            r'(?P<plain>[^.\[\]{}"]+)'
        )

    def tokenize(self, path: str) -> List[dict]:
        if not path: return []
        # Normalizacja separatorów przed tokenizacja (np. zamiana / na .)
        path = path.replace('\\', '.').replace('/', '.')

        tokens = []
        for match in self.token_regex.finditer(path):
            if match.group('quoted'):
                tokens.append({'type': 'key', 'value': match.group('quoted'), 'escaped': True})
            elif match.group('index'):
                val = match.group('index')
                tokens.append({'type': 'index', 'value': val})
            elif match.group('dynamic'):
                tokens.append({'type': 'dynamic', 'value': match.group('dynamic')})
            elif match.group('plain'):
                tokens.append({'type': 'key', 'value': match.group('plain'), 'escaped': False})
        return tokens

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