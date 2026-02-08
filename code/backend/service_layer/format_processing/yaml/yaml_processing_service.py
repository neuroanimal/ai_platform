"""
Enhanced YAML Processing Service - AI-integrated YAML processing
Combines rule-based and AI approaches for comprehensive YAML processing
"""
import os
from typing import Dict, Any, List, Optional, Tuple
from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError
from common.handler.path_handler import PathHandler
from common.engine.io_engine.yaml_io_module import YAMLIOModule
from common.engine.io_engine.json_io_module import JSONIOModule
from common.engine.io_engine.helm_io_module import HelmIOModule
from backend.service_layer.ai_engine.structure_analysis.structure_analysis_engine import StructureAnalysisEngine
from backend.service_layer.ai_engine.template_analysis.template_analysis_engine import TemplateAnalysisEngine


class YAMLProcessingService:
    """Enhanced YAML processing with AI integration"""

    def __init__(self, product: str = "AI_Platform", version: str = "1.0"):
        self.product = product
        self.version = version

        # Initialize components
        self.tracer = TraceHandler(product, version, "YAMLProcessor")
        self.path_handler = PathHandler()
        self.yaml_io = YAMLIOModule(self.tracer)
        self.json_io = JSONIOModule(self.tracer)
        self.helm_io = HelmIOModule(self.tracer)

        # AI engines
        self.structure_engine = StructureAnalysisEngine(self.tracer, self.path_handler)
        self.template_engine = TemplateAnalysisEngine(self.tracer, self.path_handler, self.structure_engine)

        self.stats = {
            "files_processed": 0,
            "lines_uncommented": 0,
            "ai_decisions": 0,
            "rule_decisions": 0,
            "hybrid_decisions": 0
        }

    def process_yaml_template(self, input_path: str, output_path: str,
                            mrcf_path: Optional[str] = None,
                            helm_path: Optional[str] = None,
                            system_size: str = "standard-system",
                            processing_mode: str = "hybrid") -> bool:
        """
        Main YAML template processing with multiple modes

        Args:
            input_path: Input YAML template file
            output_path: Output processed YAML file
            mrcf_path: Machine Readable Configuration File (JSON)
            helm_path: Helm charts directory
            system_size: System size flavor
            processing_mode: 'rule', 'ai', or 'hybrid'
        """
        try:
            self.tracer.info(f"Starting YAML processing: {processing_mode} mode")

            # Load input template
            template_lines = self.yaml_io.read_raw_lines(input_path)

            # Build knowledge model
            knowledge_model = self._build_knowledge_model(mrcf_path, helm_path)

            # Process based on mode
            if processing_mode == "rule":
                processed_lines = self._process_rule_based(template_lines, knowledge_model)
            elif processing_mode == "ai":
                processed_lines = self._process_ai_based(template_lines, knowledge_model)
            else:  # hybrid
                processed_lines = self._process_hybrid(template_lines, knowledge_model)

            # Write output
            success = self.yaml_io.write_raw_lines(processed_lines, output_path)

            if success:
                self.stats["files_processed"] += 1
                self.tracer.info(f"YAML processing completed: {output_path}")

            return success

        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "YAML template processing")
            return False

    def _build_knowledge_model(self, mrcf_path: Optional[str], helm_path: Optional[str]) -> Dict[str, Any]:
        """Build comprehensive knowledge model from available sources"""
        knowledge = {
            "helm_data": {},
            "flat_json_data": {},
            "parameters": []
        }

        # Load Helm data
        if helm_path and os.path.exists(helm_path):
            self.tracer.info(f"Loading Helm charts from: {helm_path}")
            knowledge["helm_data"] = self.helm_io.read_all_charts(helm_path)

        # Load MRCF data
        if mrcf_path and os.path.exists(mrcf_path):
            self.tracer.info(f"Loading MRCF from: {mrcf_path}")
            mrcf_data = self.json_io.read_file(mrcf_path)

            # Extract flat JSON and parameters
            if isinstance(mrcf_data, dict):
                if "parameters" in mrcf_data:
                    knowledge["parameters"] = mrcf_data["parameters"]

                # Flatten for path-based lookup
                knowledge["flat_json_data"] = self.json_io._flatten_dict(mrcf_data)

        # Build structure model
        self.structure_engine.build_from_sources(
            knowledge["helm_data"],
            knowledge["flat_json_data"]
        )

        # Ingest parameters
        if knowledge["parameters"]:
            self.structure_engine.ingest_json_parameters(knowledge["parameters"])

        return knowledge

    def _process_rule_based(self, template_lines: List[str], knowledge_model: Dict[str, Any]) -> List[str]:
        """Rule-based processing (original uncomment-00 approach)"""
        self.tracer.info("Processing with rule-based approach")

        processed_lines = []
        uncommented_count = 0

        for line_content in template_lines:
            processed_line = line_content

            # Simple rule-based uncommenting
            if self._should_uncomment_rule_based(line_content, knowledge_model):
                processed_line = self._uncomment_line(line_content)
                uncommented_count += 1
                self.stats["rule_decisions"] += 1

            processed_lines.append(processed_line)

        self.stats["lines_uncommented"] += uncommented_count
        self.tracer.info(f"Rule-based processing: {uncommented_count} lines uncommented")

        return processed_lines

    def _process_ai_based(self, template_lines: List[str], knowledge_model: Dict[str, Any]) -> List[str]:
        """AI-based processing using template analysis engine"""
        self.tracer.info("Processing with AI-based approach")

        # Analyze template with AI
        self.template_engine.process_template(template_lines)

        processed_lines = []
        uncommented_count = 0

        for line in self.template_engine.lines:
            processed_line = line.raw_content

            # AI-based decision
            if self._should_uncomment_ai_based(line):
                processed_line = self._uncomment_line(line.raw_content)
                uncommented_count += 1
                self.stats["ai_decisions"] += 1

            processed_lines.append(processed_line)

        self.stats["lines_uncommented"] += uncommented_count
        self.tracer.info(f"AI-based processing: {uncommented_count} lines uncommented")

        return processed_lines

    def _process_hybrid(self, template_lines: List[str], knowledge_model: Dict[str, Any]) -> List[str]:
        """Hybrid processing combining rule-based and AI approaches"""
        self.tracer.info("Processing with hybrid approach")

        # First, analyze with AI
        self.template_engine.process_template(template_lines)

        processed_lines = []
        uncommented_count = 0

        for line in self.template_engine.lines:
            processed_line = line.raw_content

            # Hybrid decision making
            should_uncomment, decision_type = self._should_uncomment_hybrid(line, knowledge_model)

            if should_uncomment:
                processed_line = self._uncomment_line(line.raw_content)
                uncommented_count += 1

                if decision_type == "rule":
                    self.stats["rule_decisions"] += 1
                elif decision_type == "ai":
                    self.stats["ai_decisions"] += 1
                else:
                    self.stats["hybrid_decisions"] += 1

            processed_lines.append(processed_line)

        self.stats["lines_uncommented"] += uncommented_count
        self.tracer.info(f"Hybrid processing: {uncommented_count} lines uncommented")

        return processed_lines

    def _should_uncomment_rule_based(self, line_content: str, knowledge_model: Dict[str, Any]) -> bool:
        """Rule-based decision for uncommenting"""
        stripped = line_content.strip()

        # Must be commented
        if not stripped.startswith('#'):
            return False

        # Must have key:value structure
        content_after_hash = stripped.lstrip('#').strip()
        if ':' not in content_after_hash:
            return False

        # Extract key
        key_match = re.match(r'^([a-zA-Z0-9_\\-\\.]+)\\s*:', content_after_hash)
        if not key_match:
            return False

        key = key_match.group(1)

        # Check in flat JSON data
        flat_data = knowledge_model.get("flat_json_data", {})
        for path in flat_data.keys():
            if key in path.split('.'):
                return True

        # Check in Helm data
        helm_data = knowledge_model.get("helm_data", {})
        return self._key_exists_in_dict(key, helm_data)

    def _should_uncomment_ai_based(self, line) -> bool:
        """AI-based decision for uncommenting"""
        # Must be classified as inactive data
        if line.classification != "INACTIVE_DATA":
            return False

        # Must have structure node match
        if not line.structure_node:
            return False

        # Confidence threshold
        if line.confidence < 0.7:
            return False

        return True

    def _should_uncomment_hybrid(self, line, knowledge_model: Dict[str, Any]) -> Tuple[bool, str]:
        """Hybrid decision combining rule-based and AI approaches"""
        # AI decision first
        ai_decision = self._should_uncomment_ai_based(line)

        # Rule-based decision
        rule_decision = self._should_uncomment_rule_based(line.raw_content, knowledge_model)

        # Decision logic
        if ai_decision and rule_decision:
            return True, "hybrid"
        elif ai_decision and line.confidence > 0.8:
            return True, "ai"
        elif rule_decision:
            return True, "rule"
        elif ai_decision and line.confidence > 0.6:
            # Lower threshold for AI if it has some confidence
            return True, "ai"

        return False, "none"

    def _uncomment_line(self, line_content: str) -> str:
        """Uncomment a line while preserving formatting"""
        stripped = line_content.lstrip()
        if stripped.startswith('#'):
            # Remove first # and any immediately following space
            uncommented = stripped[1:].lstrip(' ')
            # Preserve original indentation
            indent = line_content[:len(line_content) - len(line_content.lstrip())]
            return indent + uncommented
        return line_content

    def _key_exists_in_dict(self, key: str, data: Dict[str, Any]) -> bool:
        """Check if key exists anywhere in nested dictionary"""
        if isinstance(data, dict):
            if key in data:
                return True
            for value in data.values():
                if self._key_exists_in_dict(key, value):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._key_exists_in_dict(key, item):
                    return True
        return False

    def process_batch(self, input_dir: str, output_dir: str, **kwargs) -> Dict[str, bool]:
        """Process multiple YAML files in batch"""
        results = {}

        if not os.path.exists(input_dir):
            self.tracer.error(f"Input directory not found: {input_dir}")
            return results

        os.makedirs(output_dir, exist_ok=True)

        for filename in os.listdir(input_dir):
            if filename.endswith(('.yaml', '.yml')):
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, filename)

                self.tracer.info(f"Processing batch file: {filename}")
                success = self.process_yaml_template(input_path, output_path, **kwargs)
                results[filename] = success

        return results

    def validate_yaml_syntax(self, file_path: str) -> bool:
        """Validate YAML file syntax"""
        return self.yaml_io.validate_yaml(file_path)

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get comprehensive processing summary"""
        return {
            "service": "YAMLProcessingService",
            "stats": self.stats,
            "components": {
                "yaml_io": self.yaml_io.get_summary(),
                "json_io": self.json_io.get_summary(),
                "helm_io": self.helm_io.get_summary(),
                "structure_engine": self.structure_engine.get_summary(),
                "template_engine": self.template_engine.get_summary(),
                "path_handler": self.path_handler.get_summary()
            }
        }