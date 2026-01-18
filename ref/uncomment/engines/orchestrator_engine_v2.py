from common.trace_handler import TraceHandler
from common.path_handler import PathHandler
from common.error_handler import ErrorHandler, BaseEngineError

from engines.io_engine.helm_module import HelmModule
from engines.io_engine.yaml_module import YAMLModule
from engines.io_engine.json_module import JSONModule
from engines.ai_engine.structure_model import StructureModel
from engines.ai_engine.template_model import TemplateModel
from engines.yaml_processor.yaml_processor_engine import YAMLProcessorEngine


class OrchestratorEngine:
    """
    Master Engine managing data flow between modules.
    Implements: Read -> Model -> Process -> Fix -> Write loop.
    Now includes YAML Processor Engine for direct template processing.
    """
    def __init__(self, product: str, version: str, config: dict):
        self.product = product
        self.version = version
        self.config = config
        
        # Initialize Handlers
        self.tracer = TraceHandler(product, version, "Orchestrator")
        self.path_handler = PathHandler()
        
        # Initialize IO Modules
        self.helm_io = HelmModule(self.tracer)
        self.yaml_io = YAMLModule(self.tracer)
        self.json_io = JSONModule(self.tracer)
        
        # Initialize AI Engines
        self.structure_model = StructureModel(self.tracer, self.path_handler)
        self.template_model = TemplateModel(self.tracer, self.path_handler, self.structure_model)
        
        # Initialize YAML Processor Engine (from uncomment-00)
        self.yaml_processor = YAMLProcessorEngine(self.tracer)

    def run_uncomment_process(self):
        """Main end-to-end process using ML-based approach."""
        try:
            self.tracer.info(f"--- START ML PROCESS: {self.product} v{self.version} ---")

            # 1. READ INPUT DATA
            helm_data = self.helm_io.read_all_charts(self._get_path("input/structure/helm"))
            flat_json = {}
            json_params = self.json_io.read_parameters(self._get_path("input/structure/flat/params.json"))
            template_lines = self._read_raw_template(self._get_path("input/template/values.yaml"))

            # 2. BUILD KNOWLEDGE MODEL (Structure Model)
            self.structure_model.build_from_sources(helm_data, flat_json)
            self.structure_model.ingest_json_parameters(json_params)
            self.structure_model.trace_sample_paths(50)

            # 3. TEMPLATE ANALYSIS AND CLASSIFICATION (Template Model)
            self.template_model.process_template(template_lines)

            # 4. DECISION LOOP (UNCOMMENTING PROCESS)
            processed_lines = self._execute_uncomment_logic()

            # 5. WRITE OUTPUT (First iteration)
            self._write_output_template(processed_lines)

            self.tracer.info("--- ML PROCESS COMPLETED SUCCESSFULLY ---")

        except Exception as e:
            ErrorHandler.handle(e, self.tracer)

    def run_direct_yaml_process(self, mrcf_path: str = None, helm_path: str = None, 
                               system_size: str = "standard-system"):
        """Direct YAML processing using uncomment-00 approach."""
        try:
            self.tracer.info(f"--- START DIRECT YAML PROCESS: {self.product} v{self.version} ---")
            
            input_path = self._get_path("input/template/values.yaml")
            output_path = self._get_path("output/template/uncommented_values_direct.yaml")
            
            # Use YAML Processor Engine directly
            success = self.yaml_processor.process_yaml_template(
                input_path=input_path,
                output_path=output_path,
                mrcf_path=mrcf_path,
                helm_path=helm_path,
                system_size=system_size
            )
            
            if success:
                self.tracer.info("--- DIRECT YAML PROCESS COMPLETED SUCCESSFULLY ---")
            else:
                self.tracer.error("--- DIRECT YAML PROCESS FAILED ---")
                
            return success
            
        except Exception as e:
            ErrorHandler.handle(e, self.tracer)
            return False

    def run_hybrid_process(self, mrcf_path: str = None, helm_path: str = None,
                          system_size: str = "standard-system"):
        """Hybrid approach: ML analysis + direct processing."""
        try:
            self.tracer.info(f"--- START HYBRID PROCESS: {self.product} v{self.version} ---")
            
            # First run ML analysis for insights
            self.tracer.info("Phase 1: ML Analysis")
            helm_data = self.helm_io.read_all_charts(self._get_path("input/structure/helm"))
            json_params = self.json_io.read_parameters(self._get_path("input/structure/flat/params.json"))
            
            self.structure_model.build_from_sources(helm_data, {})
            self.structure_model.ingest_json_parameters(json_params)
            
            # Then run direct processing
            self.tracer.info("Phase 2: Direct YAML Processing")
            input_path = self._get_path("input/template/values.yaml")
            output_path = self._get_path("output/template/uncommented_values_hybrid.yaml")
            
            success = self.yaml_processor.process_yaml_template(
                input_path=input_path,
                output_path=output_path,
                mrcf_path=mrcf_path,
                helm_path=helm_path or self._get_path("input/structure/helm"),
                system_size=system_size
            )
            
            if success:
                self.tracer.info("--- HYBRID PROCESS COMPLETED SUCCESSFULLY ---")
            else:
                self.tracer.error("--- HYBRID PROCESS FAILED ---")
                
            return success
            
        except Exception as e:
            ErrorHandler.handle(e, self.tracer)
            return False

    def _execute_uncomment_logic(self) -> list:
        """
        Decision logic: For each INACTIVE_DATA line, check if it should be 
        uncommented based on the structure model.
        """
        final_lines = []
        uncommented_count = 0
        force_uncomment_until_indent = -1

        for line in self.template_model.lines:
            content = line.raw_content

            # If we're inside a block that we forced to uncomment
            if force_uncomment_until_indent != -1:
                if line.indent_level > force_uncomment_until_indent:
                    line.classification = "INACTIVE_DATA"
                else:
                    force_uncomment_until_indent = -1

            if line.classification == "INACTIVE_DATA":
                self.tracer.debug(f"Line {line.line_number} | Template path: '{line.identified_path}' | Matched: {line.structure_node is not None}")

                # Check if this line's path exists in our knowledge model
                if line.structure_node:
                    # Success - uncomment
                    if line.structure_node.children:
                        force_uncomment_until_indent = line.indent_level
                    
                    # DECISION: If model knows this parameter, uncomment it
                    target_indent = line.structure_node.metadata['depth'] * 2
                    clean_content = line.raw_content.strip().lstrip('#').strip()
                    
                    content = f"{' ' * target_indent}{clean_content}\n"
                    uncommented_count += 1
                    self.tracer.trace_decision(
                        step="uncomment", 
                        reason=f"Found in StructureModel at path: {line.identified_path}"
                    )
                else:
                    self.tracer.debug(f"Path not found in model: {line.identified_path}")

            final_lines.append(content)
        
        self.tracer.info(f"Uncommented {uncommented_count} lines based on model.")
        return final_lines

    def _get_path(self, sub_path: str) -> str:
        """Helper to build paths according to your structure."""
        return f"data/{self.product}/{self.version}/{sub_path}"

    def _read_raw_template(self, path: str) -> list:
        with open(path, 'r', encoding='utf-8') as f:
            return f.readlines()

    def _write_output_template(self, lines: list):
        out_path = self._get_path("output/template/uncommented_values.yaml")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)