"""
Path Handler - Unified path processing and tokenization
Integrated from uncomment project with enhancements
"""
import re
from typing import List, Dict, Any, Optional


class PathHandler:
    """Advanced path processing and tokenization for various formats"""
    
    def __init__(self):
        self.stats = {"tokenized_paths": 0, "complex_paths": 0}
        
        # Regex patterns for different path types
        self.patterns = {
            "yaml_key": re.compile(r'^[a-zA-Z0-9_\-\.]+$'),
            "array_index": re.compile(r'^\[(\d+|N)\]$'),
            "dynamic_placeholder": re.compile(r'^\{\{.*\}\}$'),
            "quoted_key": re.compile(r'^["\'](.+)["\']$'),
            "grouped_key": re.compile(r'^\((.+)\)$')
        }
    
    def tokenize(self, path: str) -> List[Dict[str, str]]:
        """
        Tokenize path into structured components
        Returns list of tokens with type and value
        """
        if not path:
            return []
        
        # Normalize path separators
        normalized_path = self._normalize_path(path)
        
        # Split into tokens
        raw_tokens = self._split_path(normalized_path)
        
        # Classify each token
        tokens = []
        for token in raw_tokens:
            token_info = self._classify_token(token)
            tokens.append(token_info)
        
        self.stats["tokenized_paths"] += 1
        if len(tokens) > 5:  # Consider complex if more than 5 levels
            self.stats["complex_paths"] += 1
        
        return tokens
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path separators and format"""
        # Convert slashes to dots for consistency
        if path.startswith('/'):
            path = path.lstrip('/').replace('/', '.')
        
        # Handle array indices
        path = re.sub(r'\[(\d+)\]', r'.[N]', path)
        
        return path.strip('.')
    
    def _split_path(self, path: str) -> List[str]:
        """Split path while preserving complex tokens"""
        # Handle quoted strings and grouped expressions
        protected_tokens = []
        
        # Temporarily replace complex tokens
        def protect_token(match):
            token = match.group(0)
            placeholder = f"__TOKEN_{len(protected_tokens)}__"
            protected_tokens.append(token)
            return placeholder
        
        # Protect quoted strings and grouped expressions
        protected_path = re.sub(r'["\']([^"\']*)["\']|\(([^)]*)\)', protect_token, path)
        
        # Split by dots
        tokens = [t.strip() for t in protected_path.split('.') if t.strip()]
        
        # Restore protected tokens
        for i, token in enumerate(tokens):
            if token.startswith('__TOKEN_'):
                idx = int(token.split('_')[2].rstrip('_'))
                tokens[i] = protected_tokens[idx]
        
        return tokens
    
    def _classify_token(self, token: str) -> Dict[str, str]:
        """Classify token type and extract value"""
        token = token.strip()
        
        # Array index
        if self.patterns["array_index"].match(token):
            return {"type": "index", "value": "[N]", "original": token}
        
        # Dynamic placeholder
        if self.patterns["dynamic_placeholder"].match(token):
            return {"type": "dynamic", "value": token, "original": token}
        
        # Quoted key
        quoted_match = self.patterns["quoted_key"].match(token)
        if quoted_match:
            return {"type": "key", "value": quoted_match.group(1), "original": token}
        
        # Grouped key
        grouped_match = self.patterns["grouped_key"].match(token)
        if grouped_match:
            return {"type": "special", "value": grouped_match.group(1), "original": token}
        
        # Regular key
        if self.patterns["yaml_key"].match(token):
            return {"type": "key", "value": token, "original": token}
        
        # Special/complex key
        return {"type": "special", "value": token, "original": token}
    
    def build_path(self, tokens: List[Dict[str, str]]) -> str:
        """Build path from tokens"""
        return '.'.join(token["value"] for token in tokens)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get path processing summary"""
        return self.stats