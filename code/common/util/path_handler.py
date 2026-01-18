import re
from typing import List, Dict

class PathHandler:
    """Path tokenization, normalization, and matching."""
    
    def __init__(self):
        self.token_regex = re.compile(
            r'\"(?P<quoted>.*?)(?<!\\)\"|'
            r'\[(?P<index>.*?)\]|'
            r'\{\{(?P<dynamic>.*?)\}\}|'
            r'(?P<plain>[^.\[\]{}\"]+)'
        )
    
    def tokenize(self, path: str) -> List[Dict]:
        """Split path into tokens with metadata."""
        if not path:
            return []
        path = path.replace('\\', '.').replace('/', '.')
        
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
        """Check if paths match (with placeholder support)."""
        t_tokens = self.tokenize(template_path)
        s_tokens = self.tokenize(schema_path)
        
        if len(t_tokens) != len(s_tokens):
            return False
        
        for t, s in zip(t_tokens, s_tokens):
            if t['type'] == 'dynamic' or s['type'] == 'dynamic':
                continue
            if t['value'] != s['value']:
                return False
        return True
    
    def get_depth(self, path: str) -> int:
        """Get nesting depth."""
        return len(self.tokenize(path))
