"""
Template Analysis Engine - AI-enhanced template analysis and classification
Integrated from uncomment project with improvements
"""
import re
from typing import List, Dict, Optional, Any
from common.handler.trace_handler import TraceHandler
from common.handler.path_handler import PathHandler
from backend.service_layer.ai_engine.structure_analysis.structure_analysis_engine import StructureAnalysisEngine


class TemplateLine:
    """Enhanced template line with AI classification"""
    
    def __init__(self, raw_content: str, line_no: int):
        self.raw_content = raw_content
        self.line_no = line_no
        self.line_number = line_no
        self.indent_level = self._calculate_indent(raw_content)
        self.classification = None  # DOC, CONSTRAINT, ACTIVE_DATA, INACTIVE_DATA
        self.identified_path = None
        self.structure_node = None
        self.confidence = 1.0  # AI confidence score
        self.ai_features = {}  # AI-extracted features
        
    def _calculate_indent(self, line_str: str) -> int:
        """Calculate indentation level"""
        return len(line_str) - len(line_str.lstrip(' '))


class TemplateAnalysisEngine:
    """AI-enhanced template analysis with hybrid rule-based and ML approaches"""
    
    def __init__(self, tracer: TraceHandler, path_handler: PathHandler, structure_engine: StructureAnalysisEngine):
        self.tracer = tracer
        self.path_handler = path_handler
        self.structure_engine = structure_engine
        self.lines: List[TemplateLine] = []
        self.context_stack = []
        
        # Enhanced classification rules
        self.rules = {
            "data_pattern": re.compile(r'^\\s*#?\\s*([a-zA-Z0-9_\\-\\.]+)\\s*:\\s*(.*)'),
            "constraint_keywords": ["mandatory", "must", "do not", "readonly", "obsolete", "required"],
            "documentation_indicators": ["description", "example", "note", "warning", "info"],
            "comment_marker": "#",
            "helm_template": re.compile(r'\\{\\{.*?\\}\\}'),
            "list_item": re.compile(r'^\\s*-\\s*'),
            "yaml_key": re.compile(r'^\\s*([a-zA-Z0-9_\\-\\.]+)\\s*:')
        }
        
        self.stats = {
            "lines_processed": 0,
            "active_data": 0,
            "inactive_data": 0,
            "documentation": 0,
            "constraints": 0,
            "ai_classifications": 0,
            "path_resolutions": 0
        }
    
    def process_template(self, raw_lines: List[str]):
        """Main template processing with AI enhancements"""
        self.tracer.info("Starting AI-enhanced template analysis...")
        
        self.context_stack = []
        self.lines = []
        
        for idx, raw_content in enumerate(raw_lines):
            line = TemplateLine(raw_content, idx + 1)
            
            # Extract AI features
            self._extract_ai_features(line)
            
            # Hybrid classification (Rule-based + AI)
            self._classify_line_hybrid(line)
            
            # Enhanced path resolution
            if line.classification in ["ACTIVE_DATA", "INACTIVE_DATA"]:
                self._resolve_path_with_ai(line)
            
            self.lines.append(line)
            self.stats["lines_processed"] += 1
        
        # Post-processing with AI insights
        self._apply_ai_post_processing()
        
        self.tracer.info(f"Template analysis complete: {self.stats['lines_processed']} lines processed")
    
    def _extract_ai_features(self, line: TemplateLine):
        """Extract AI features from template line"""
        content = line.raw_content.strip()
        
        features = {
            "has_comment": content.startswith('#'),
            "has_colon": ':' in content,
            "has_helm_template": bool(self.rules["helm_template"].search(content)),
            "is_list_item": bool(self.rules["list_item"].match(content)),
            "line_length": len(content),
            "word_count": len(content.split()),
            "has_quotes": '"' in content or "'" in content,
            "has_brackets": '[' in content or ']' in content,
            "indent_ratio": line.indent_level / max(len(line.raw_content), 1),
            "uppercase_ratio": sum(1 for c in content if c.isupper()) / max(len(content), 1)
        }
        
        # Semantic features
        content_lower = content.lower()
        features.update({
            "has_constraint_words": any(kw in content_lower for kw in self.rules["constraint_keywords"]),
            "has_doc_indicators": any(ind in content_lower for ind in self.rules["documentation_indicators"]),
            "has_technical_terms": any(term in content_lower for term in ["config", "enable", "disable", "port", "host", "path"])
        })
        
        line.ai_features = features
    
    def _classify_line_hybrid(self, line: TemplateLine):
        """Hybrid classification using rules and AI features"""
        content = line.raw_content.strip()
        
        if not content:
            line.classification = "EMPTY"
            return
        
        # Rule-based classification first
        rule_classification = self._classify_with_rules(line)
        
        # AI enhancement
        ai_confidence = self._calculate_ai_confidence(line, rule_classification)
        
        # Final classification
        if ai_confidence > 0.8:
            line.classification = rule_classification
            line.confidence = ai_confidence
        else:
            # Use AI to refine classification
            line.classification = self._ai_classify(line)
            line.confidence = ai_confidence
            self.stats["ai_classifications"] += 1
        
        # Update stats
        if line.classification == "ACTIVE_DATA":
            self.stats["active_data"] += 1
        elif line.classification == "INACTIVE_DATA":
            self.stats["inactive_data"] += 1
        elif line.classification == "DOCUMENTATION":
            self.stats["documentation"] += 1
        elif line.classification == "CONSTRAINT":
            self.stats["constraints"] += 1
    
    def _classify_with_rules(self, line: TemplateLine) -> str:
        """Traditional rule-based classification"""
        content = line.raw_content.strip()
        
        # Active data (no comment marker, has key:value structure)
        if not content.startswith(self.rules["comment_marker"]):
            if self.rules["yaml_key"].match(content) or self.rules["list_item"].match(content):
                return "ACTIVE_DATA"
            else:
                return "DOCUMENTATION"
        
        # Commented content
        content_after_hash = content.lstrip('#').strip()
        
        # Check for data structure
        if self.rules["yaml_key"].match(content_after_hash):
            # Additional checks for data vs documentation
            if line.ai_features.get("has_helm_template", False):
                return "INACTIVE_DATA"
            elif line.ai_features.get("has_constraint_words", False):
                return "CONSTRAINT"
            elif line.ai_features.get("has_doc_indicators", False):
                return "DOCUMENTATION"
            else:
                return "INACTIVE_DATA"
        
        # Constraint detection
        if line.ai_features.get("has_constraint_words", False):
            return "CONSTRAINT"
        
        return "DOCUMENTATION"
    
    def _calculate_ai_confidence(self, line: TemplateLine, classification: str) -> float:
        """Calculate AI confidence score for classification"""
        features = line.ai_features
        confidence = 0.5  # Base confidence
        
        # Confidence boosters
        if classification == "ACTIVE_DATA":
            if features.get("has_colon", False) and not features.get("has_comment", False):
                confidence += 0.4
            if features.get("has_helm_template", False):
                confidence += 0.2
        
        elif classification == "INACTIVE_DATA":
            if features.get("has_comment", False) and features.get("has_colon", False):
                confidence += 0.3
            if features.get("has_helm_template", False):
                confidence += 0.3
        
        elif classification == "CONSTRAINT":
            if features.get("has_constraint_words", False):
                confidence += 0.4
        
        elif classification == "DOCUMENTATION":
            if features.get("has_doc_indicators", False):
                confidence += 0.3
            if features.get("word_count", 0) > 5:
                confidence += 0.2
        
        return min(1.0, confidence)
    
    def _ai_classify(self, line: TemplateLine) -> str:
        """AI-based classification refinement"""
        features = line.ai_features
        
        # Simple decision tree (could be replaced with ML model)
        if features.get("has_colon", False):
            if features.get("has_comment", False):
                if features.get("has_helm_template", False):
                    return "INACTIVE_DATA"
                elif features.get("has_constraint_words", False):
                    return "CONSTRAINT"
                else:
                    return "INACTIVE_DATA"
            else:
                return "ACTIVE_DATA"
        
        elif features.get("has_constraint_words", False):
            return "CONSTRAINT"
        
        elif features.get("word_count", 0) > 3:
            return "DOCUMENTATION"
        
        return "DOCUMENTATION"
    
    def _resolve_path_with_ai(self, line: TemplateLine):
        """AI-enhanced path resolution with backtracking"""
        content = line.raw_content.lstrip().lstrip('#').strip()
        
        # Extract key
        key_match = self.rules["yaml_key"].match(content.lstrip('- '))
        current_key = key_match.group(1) if key_match else (
            "[N]" if content.startswith('-') else None
        )
        
        if not current_key:
            return
        
        # AI-enhanced backtracking
        best_parent_node = None
        new_stack_depth = -1
        max_confidence = 0.0
        
        # Search context stack with AI scoring
        for depth in range(len(self.context_stack) - 1, -1, -1):
            parent_info = self.context_stack[depth]
            parent_node = parent_info.get('node')
            
            if parent_node and self._can_be_child(parent_node, current_key):
                confidence = self._calculate_parent_confidence(parent_node, current_key, line)
                if confidence > max_confidence:
                    best_parent_node = parent_node
                    new_stack_depth = depth
                    max_confidence = confidence
        
        if best_parent_node and max_confidence > 0.5:
            # Update context stack
            self.context_stack = self.context_stack[:new_stack_depth + 1]
            
            # Get child node
            child_node = self._get_child_node(best_parent_node, current_key)
            if child_node:
                line.structure_node = child_node
                parent_path = self.context_stack[-1]['path']
                line.identified_path = f"{parent_path}.{current_key}".strip('.')
                line.confidence = max_confidence
                
                # Add to context stack
                self.context_stack.append({
                    'indent': line.indent_level,
                    'path': line.identified_path,
                    'node': child_node
                })
                
                self.stats["path_resolutions"] += 1
    
    def _can_be_child(self, parent_node, child_key: str) -> bool:
        """Check if child_key can be a child of parent_node"""
        return (child_key in parent_node.children or 
                "[N]" in parent_node.children or
                parent_node.node_type in ["object", "key"])
    
    def _calculate_parent_confidence(self, parent_node, child_key: str, line: TemplateLine) -> float:
        """Calculate confidence that parent_node is correct parent for child_key"""
        confidence = 0.5
        
        # Direct child match
        if child_key in parent_node.children:
            confidence += 0.4
        
        # Array element match
        elif "[N]" in parent_node.children:
            confidence += 0.3
        
        # Source consistency
        if parent_node.metadata.get("source") in ["helm", "both"]:
            confidence += 0.1
        
        # Usage frequency
        usage_count = parent_node.metadata.get("usage_count", 0)
        if usage_count > 0:
            confidence += min(0.2, usage_count * 0.02)
        
        return min(1.0, confidence)
    
    def _get_child_node(self, parent_node, child_key: str):
        """Get child node with fallback to array element"""
        if child_key in parent_node.children:
            return parent_node.children[child_key]
        elif "[N]" in parent_node.children:
            return parent_node.children["[N]"]
        return None
    
    def _apply_ai_post_processing(self):
        """Apply AI-based post-processing improvements"""
        # Analyze classification patterns
        self._analyze_classification_patterns()
        
        # Refine path resolutions
        self._refine_path_resolutions()
        
        self.tracer.info("Applied AI post-processing enhancements")
    
    def _analyze_classification_patterns(self):
        """Analyze and improve classification patterns"""
        # Group lines by classification
        classifications = {}
        for line in self.lines:
            if line.classification not in classifications:
                classifications[line.classification] = []
            classifications[line.classification].append(line)
        
        # Look for patterns and adjust confidence
        for classification, lines in classifications.items():
            if len(lines) > 1:
                avg_confidence = sum(line.confidence for line in lines) / len(lines)
                for line in lines:
                    if abs(line.confidence - avg_confidence) > 0.3:
                        line.confidence = (line.confidence + avg_confidence) / 2
    
    def _refine_path_resolutions(self):
        """Refine path resolutions using AI insights"""
        resolved_lines = [line for line in self.lines if line.structure_node]
        
        # Analyze resolution patterns
        for line in resolved_lines:
            if line.confidence < 0.7:
                # Try alternative resolution
                alternative_node = self.structure_engine.resolve_path_context(line.identified_path)
                if alternative_node and alternative_node != line.structure_node:
                    line.structure_node = alternative_node
                    line.confidence = min(1.0, line.confidence + 0.2)
    
    def get_inactive_data_lines(self) -> List[TemplateLine]:
        """Get lines classified as inactive data"""
        return [line for line in self.lines if line.classification == "INACTIVE_DATA"]
    
    def get_classification_summary(self) -> Dict[str, Any]:
        """Get classification summary with AI insights"""
        return {
            "total_lines": len(self.lines),
            "classifications": {
                "active_data": self.stats["active_data"],
                "inactive_data": self.stats["inactive_data"],
                "documentation": self.stats["documentation"],
                "constraints": self.stats["constraints"]
            },
            "ai_metrics": {
                "ai_classifications": self.stats["ai_classifications"],
                "path_resolutions": self.stats["path_resolutions"],
                "avg_confidence": sum(line.confidence for line in self.lines) / len(self.lines) if self.lines else 0
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return self.stats