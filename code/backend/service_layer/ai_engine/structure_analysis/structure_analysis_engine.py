"""
Structure Analysis Engine - AI-enhanced structure modeling
Integrated from uncomment project with improvements
"""
import re
from typing import Dict, Any, Optional, List
from common.handler.trace_handler import TraceHandler
from common.handler.path_handler import PathHandler


class StructureNode:
    """Enhanced structure node with metadata"""

    def __init__(self, name: str, node_type: str = "key", depth: int = 0):
        self.name = name
        self.node_type = node_type  # 'object', 'array', 'string', 'boolean', etc.
        self.depth = depth
        self.children: Dict[str, 'StructureNode'] = {}
        self.metadata = {
            "source": None,          # 'helm', 'json_params', 'both'
            "origin": "inferred",    # 'parameter_tree', 'directory_tree', 'path_structure'
            "data_type": "unknown",  # 'string', 'integer', etc.
            "mandatory": "no",
            "depth": depth,
            "description": None,
            "is_array_element": False,
            "confidence": 1.0,       # AI confidence score
            "usage_count": 0         # How often this path is referenced
        }


class StructureAnalysisEngine:
    """AI-enhanced structure analysis and modeling"""

    def __init__(self, tracer: TraceHandler, path_handler: PathHandler):
        self.tracer = tracer
        self.path_handler = path_handler
        self.root = StructureNode("root")
        self.stats = {
            "nodes_created": 0,
            "dynamic_links": 0,
            "ai_inferences": 0,
            "confidence_adjustments": 0
        }

    def build_from_sources(self, helm_data: Dict[str, Any], flat_json_data: Dict[str, Any]):
        """Build unified structure model from multiple sources"""
        self.tracer.info("Building structure model from sources...")

        # Build skeleton from Helm data (primary source)
        if helm_data:
            self._ingest_dict(helm_data, source="helm")

        # Enrich with flat JSON data
        for path, value in flat_json_data.items():
            self._ingest_flat_path(path, value, source="flat_json")

        # Apply AI enhancements
        self._apply_ai_enhancements()

        self.tracer.info(f"Structure model built: {self.stats['nodes_created']} nodes created")

    def ingest_json_parameters(self, parameters: List[Dict[str, Any]]):
        """Process parameter definitions with AI-enhanced path resolution"""
        for param in parameters:
            path_val = param.get("path") or param.get("name")
            if not path_val:
                self.tracer.error("Parameter missing both 'path' and 'name' fields")
                continue

            # Enhanced tokenization
            tokens = self._tokenize_complex_path(path_val)

            # Build path with AI assistance
            current = self.root
            for i, token in enumerate(tokens):
                is_leaf = (i == len(tokens) - 1)

                # Create or get node
                if token not in current.children:
                    node_type = self._determine_node_type_from_json(token, is_leaf, param.get("format"))
                    node = StructureNode(token, node_type, i)
                    current.children[token] = node
                    self.stats["nodes_created"] += 1

                current = current.children[token]

                # Update metadata
                if current.metadata["source"] is None:
                    current.metadata["source"] = "json_params"
                elif current.metadata["source"] != "json_params":
                    current.metadata["source"] = "both"

                # Leaf node gets full parameter metadata
                if is_leaf:
                    current.metadata.update({
                        "origin": "parameter_definition",
                        "mandatory": param.get("mandatory", "no"),
                        "data_type": param.get("format", "string"),
                        "description": param.get("description", ""),
                        "confidence": 1.0
                    })

    def resolve_path_context(self, raw_path: str) -> Optional[StructureNode]:
        """AI-enhanced path resolution with fuzzy matching"""
        tokens = self._tokenize_path_for_resolution(raw_path)
        current = self.root
        confidence = 1.0

        for i, token in enumerate(tokens):
            # Direct match
            if token in current.children:
                current = current.children[token]
                current.metadata["usage_count"] += 1

            # Array element match
            elif "[N]" in current.children:
                list_node = current.children["[N]"]
                if token in list_node.children:
                    current = list_node.children[token]
                else:
                    current = list_node
                confidence *= 0.9  # Slight confidence reduction

            # Dynamic/fuzzy match
            else:
                match_node = self._find_fuzzy_match(current, token)
                if match_node:
                    current = match_node
                    confidence *= 0.7  # Confidence reduction for fuzzy match
                    self.stats["ai_inferences"] += 1
                else:
                    return None

        # Update confidence if it changed
        if confidence < current.metadata["confidence"]:
            current.metadata["confidence"] = confidence
            self.stats["confidence_adjustments"] += 1

        return current

    def _ingest_dict(self, data: Any, parent_node: StructureNode = None, depth: int = 0, source: str = "helm"):
        """Recursively process nested dictionary"""
        if parent_node is None:
            parent_node = self.root

        if isinstance(data, dict):
            for key, value in data.items():
                node = self._get_or_create_node(parent_node, key, "key", depth)
                node.metadata["source"] = source
                node.metadata["data_type"] = type(value).__name__
                self._ingest_dict(value, node, depth + 1, source=source)

        elif isinstance(data, list):
            node = self._get_or_create_node(parent_node, "[N]", "index", depth)
            node.metadata["is_array_element"] = True
            node.metadata["source"] = source
            if data:
                self._ingest_dict(data[0], node, depth + 1, source=source)

    def _ingest_flat_path(self, path: str, value: Any, source: str):
        """Process flat path with enhanced tokenization"""
        tokens = self.path_handler.tokenize(path)
        current = self.root

        for i, token_info in enumerate(tokens):
            token_val = token_info['value']
            token_type = token_info['type']

            if token_type == 'dynamic':
                self.stats["dynamic_links"] += 1

            current = self._get_or_create_node(current, token_val, token_type, i)

            # Update source metadata
            if current.metadata["source"] == "helm":
                current.metadata["source"] = "both"
            elif current.metadata["source"] is None:
                current.metadata["source"] = source

            # Set data type for leaf nodes
            if i == len(tokens) - 1:
                current.metadata["data_type"] = type(value).__name__

    def _tokenize_complex_path(self, path: str) -> List[str]:
        """Enhanced path tokenization with AI assistance"""
        # Normalize array indices
        path = re.sub(r'\[(\d+)\]', '.[N]', path)

        # Handle different path formats
        if path.startswith('/'):
            path = path.lstrip('/').replace('/', '.')

        # Complex tokenization with protection for special tokens
        protected_tokens = []

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

        # Normalize array indices
        return [re.sub(r'\[(\d+)\]', '[N]', t) for t in tokens]

    def _tokenize_path_for_resolution(self, path: str) -> List[str]:
        """Simplified tokenization for path resolution"""
        return [t for t in path.split('.') if t]

    def _determine_node_type_from_json(self, token: str, is_leaf: bool, param_format: str = None) -> str:
        """Determine node type from JSON parameter format"""
        if token == "[N]":
            return "array"

        if is_leaf and param_format:
            type_mapping = {
                "string": "string",
                "boolean": "boolean",
                "integer": "integer",
                "number": "number"
            }
            return type_mapping.get(param_format, "string")

        return "object"

    def _find_fuzzy_match(self, parent_node: StructureNode, token: str) -> Optional[StructureNode]:
        """AI-enhanced fuzzy matching for dynamic paths"""
        # Look for dynamic nodes
        dynamic_nodes = [n for n in parent_node.children.values() if n.node_type == "dynamic"]
        if dynamic_nodes:
            return dynamic_nodes[0]

        # Look for similar keys (simple similarity)
        for child_name, child_node in parent_node.children.items():
            if self._calculate_similarity(token, child_name) > 0.8:
                return child_node

        return None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Simple string similarity calculation"""
        if str1 == str2:
            return 1.0

        # Simple Levenshtein-like similarity
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0

        # Count common characters
        common = sum(1 for a, b in zip(str1, str2) if a == b)
        return common / max_len

    def _get_or_create_node(self, parent: StructureNode, name: str, node_type: str, depth: int) -> StructureNode:
        """Get existing node or create new one"""
        if name not in parent.children:
            new_node = StructureNode(name, node_type, depth)
            new_node.metadata["depth"] = depth
            parent.children[name] = new_node
            self.stats["nodes_created"] += 1
            return new_node
        return parent.children[name]

    def _apply_ai_enhancements(self):
        """Apply AI-based enhancements to the structure model"""
        # Analyze patterns and adjust confidence scores
        self._analyze_usage_patterns()

        # Infer missing relationships
        self._infer_relationships()

        self.tracer.info(f"Applied AI enhancements: {self.stats['ai_inferences']} inferences made")

    def _analyze_usage_patterns(self):
        """Analyze usage patterns to adjust confidence scores"""
        def analyze_node(node: StructureNode):
            # Nodes with higher usage get higher confidence
            if node.metadata["usage_count"] > 5:
                node.metadata["confidence"] = min(1.0, node.metadata["confidence"] + 0.1)

            # Recurse to children
            for child in node.children.values():
                analyze_node(child)

        analyze_node(self.root)

    def _infer_relationships(self):
        """Infer missing relationships between nodes"""
        # This could be enhanced with more sophisticated AI algorithms
        pass

    def trace_sample_paths(self, limit: int = 50):
        """Generate sample paths for debugging"""
        self.tracer.info("Generating sample paths from structure model...")
        all_paths = self._flatten_node(self.root)

        sample = list(all_paths.keys())[:limit]
        self.tracer.info(f"--- SAMPLE PATHS ({len(sample)}): ---")
        for path in sample:
            source = all_paths[path]
            self.tracer.info(f"  [PATH] ({source}): {path}")
        self.tracer.info("---" + "-" * 40)

    def _flatten_node(self, node: StructureNode, parent_path: str = "") -> Dict[str, str]:
        """Flatten node tree to path dictionary"""
        items = {}
        for name, child_node in node.children.items():
            new_path = f"{parent_path}.{name}" if parent_path else name
            items[new_path] = child_node.metadata.get("source", "unknown")
            items.update(self._flatten_node(child_node, new_path))
        return items

    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary"""
        return self.stats