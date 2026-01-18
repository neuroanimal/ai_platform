"""
Unified Orchestrator Engine - Master orchestrator for all processing modes
Integrates rule-based, AI-based, and hybrid processing approaches
"""
import os
from typing import Dict, Any, Optional, List
from enum import Enum

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, BaseEngineError
from backend.service_layer.format_processing.yaml.yaml_processing_service import YAMLProcessingService
from backend.service_layer.schema_processing.jsonschema_processing_service import JSONSchemaProcessingService


class ProcessingMode(Enum):
    """Processing mode enumeration"""
    RULE_BASED = "rule"
    AI_BASED = "ai"
    HYBRID = "hybrid"
    ML_ANALYSIS = "ml"
    DIRECT_PROCESSING = "direct"


class UnifiedOrchestratorEngine:
    """
    Master orchestrator managing all processing capabilities
    Supports multiple processing modes and format types
    """
    
    def __init__(self, product: str = "AI_Platform", version: str = "1.0", config: Optional[Dict[str, Any]] = None):
        self.product = product
        self.version = version
        self.config = config or {}
        
        # Initialize tracer
        self.tracer = TraceHandler(product, version, "UnifiedOrchestrator")
        
        # Initialize processing services
        self.yaml_service = YAMLProcessingService(product, version)
        self.jsonschema_service = JSONSchemaProcessingService(product, version)
        
        # Processing statistics
        self.stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "yaml_operations": 0,
            "json_operations": 0,
            "hybrid_operations": 0,
            "ai_operations": 0,
            "rule_operations": 0
        }
    
    def process_yaml_template(self, input_path: str, output_path: str,
                            mode: ProcessingMode = ProcessingMode.HYBRID,
                            mrcf_path: Optional[str] = None,
                            helm_path: Optional[str] = None,
                            system_size: str = "standard-system") -> bool:
        """
        Process YAML template with specified mode
        
        Args:
            input_path: Input YAML template file
            output_path: Output processed YAML file
            mode: Processing mode (rule, ai, hybrid)
            mrcf_path: Machine Readable Configuration File
            helm_path: Helm charts directory
            system_size: System size flavor
        """
        try:
            self.tracer.info(f"Starting YAML processing: {mode.value} mode")
            self.stats["total_operations"] += 1
            self.stats["yaml_operations"] += 1
            
            # Map mode to service parameter
            processing_mode = mode.value
            if mode == ProcessingMode.ML_ANALYSIS:
                processing_mode = "ai"
            elif mode == ProcessingMode.DIRECT_PROCESSING:
                processing_mode = "rule"
            
            # Process with YAML service
            success = self.yaml_service.process_yaml_template(
                input_path=input_path,
                output_path=output_path,
                mrcf_path=mrcf_path,
                helm_path=helm_path,
                system_size=system_size,
                processing_mode=processing_mode
            )
            
            if success:
                self.stats["successful_operations"] += 1
                self._update_mode_stats(mode)
                self.tracer.info(f"YAML processing completed successfully: {output_path}")
            else:
                self.stats["failed_operations"] += 1
                self.tracer.error(f"YAML processing failed: {input_path}")
            
            return success
            
        except Exception as e:
            self.stats["failed_operations"] += 1
            ErrorHandler.handle(e, self.tracer, "YAML template processing")
            return False
    
    def process_json_schema(self, input_path: str, output_path: str,
                          operation: str = "reorder",
                          **kwargs) -> bool:
        """
        Process JSON Schema with specified operation
        
        Args:
            input_path: Input JSON Schema file
            output_path: Output processed JSON Schema file
            operation: Processing operation (reorder, validate, analyze)
        """
        try:
            self.tracer.info(f"Starting JSON Schema processing: {operation}")
            self.stats["total_operations"] += 1
            self.stats["json_operations"] += 1
            
            # Process with JSON Schema service
            if operation == "reorder":
                success = self.jsonschema_service.reorder_schema(input_path, output_path, **kwargs)
            elif operation == "validate":
                success = self.jsonschema_service.validate_schema(input_path)
            elif operation == "analyze":
                analysis = self.jsonschema_service.analyze_schema_complexity(input_path)
                success = analysis is not None
            else:
                raise BaseEngineError(f"Unknown JSON Schema operation: {operation}")
            
            if success:
                self.stats["successful_operations"] += 1
                self.tracer.info(f"JSON Schema processing completed: {output_path}")
            else:
                self.stats["failed_operations"] += 1
                self.tracer.error(f"JSON Schema processing failed: {input_path}")
            
            return success
            
        except Exception as e:
            self.stats["failed_operations"] += 1
            ErrorHandler.handle(e, self.tracer, "JSON Schema processing")
            return False
    
    def run_ml_analysis_workflow(self, input_path: str, output_dir: str,
                                mrcf_path: Optional[str] = None,
                                helm_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run comprehensive ML analysis workflow
        
        Args:
            input_path: Input YAML template
            output_dir: Output directory for results
            mrcf_path: MRCF file path
            helm_path: Helm charts path
        """
        try:
            self.tracer.info("Starting ML analysis workflow")
            os.makedirs(output_dir, exist_ok=True)
            
            results = {
                "success": False,
                "outputs": {},
                "analysis": {},
                "errors": []
            }
            
            # Phase 1: AI-based analysis
            ai_output = os.path.join(output_dir, "ai_processed.yaml")
            ai_success = self.process_yaml_template(
                input_path, ai_output,
                mode=ProcessingMode.AI_BASED,
                mrcf_path=mrcf_path,
                helm_path=helm_path
            )
            results["outputs"]["ai_processed"] = ai_output if ai_success else None
            
            # Phase 2: Rule-based processing
            rule_output = os.path.join(output_dir, "rule_processed.yaml")
            rule_success = self.process_yaml_template(
                input_path, rule_output,
                mode=ProcessingMode.RULE_BASED,
                mrcf_path=mrcf_path,
                helm_path=helm_path
            )
            results["outputs"]["rule_processed"] = rule_output if rule_success else None
            
            # Phase 3: Hybrid processing
            hybrid_output = os.path.join(output_dir, "hybrid_processed.yaml")
            hybrid_success = self.process_yaml_template(
                input_path, hybrid_output,
                mode=ProcessingMode.HYBRID,
                mrcf_path=mrcf_path,
                helm_path=helm_path
            )
            results["outputs"]["hybrid_processed"] = hybrid_output if hybrid_success else None
            
            # Generate analysis report
            results["analysis"] = self._generate_analysis_report()
            results["success"] = any([ai_success, rule_success, hybrid_success])
            
            self.tracer.info("ML analysis workflow completed")
            return results
            
        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "ML analysis workflow")
            return {"success": False, "error": str(e)}
    
    def run_batch_processing(self, input_dir: str, output_dir: str,
                           file_pattern: str = "*.yaml",
                           mode: ProcessingMode = ProcessingMode.HYBRID,
                           **kwargs) -> Dict[str, Any]:
        """
        Run batch processing on multiple files
        
        Args:
            input_dir: Input directory
            output_dir: Output directory
            file_pattern: File pattern to match
            mode: Processing mode
        """
        try:
            self.tracer.info(f"Starting batch processing: {file_pattern} in {input_dir}")
            
            if not os.path.exists(input_dir):
                raise BaseEngineError(f"Input directory not found: {input_dir}")
            
            os.makedirs(output_dir, exist_ok=True)
            
            results = {
                "total_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "file_results": {},
                "errors": []
            }
            
            # Process files based on pattern
            import glob
            pattern_path = os.path.join(input_dir, file_pattern)
            files = glob.glob(pattern_path)
            
            results["total_files"] = len(files)
            
            for file_path in files:
                filename = os.path.basename(file_path)
                output_path = os.path.join(output_dir, filename)
                
                try:
                    if file_pattern.endswith(('.yaml', '.yml')):
                        success = self.process_yaml_template(file_path, output_path, mode, **kwargs)
                    elif file_pattern.endswith('.json'):
                        success = self.process_json_schema(file_path, output_path, **kwargs)
                    else:
                        success = False
                        results["errors"].append(f"Unsupported file type: {filename}")
                    
                    results["file_results"][filename] = success
                    if success:
                        results["successful_files"] += 1
                    else:
                        results["failed_files"] += 1
                        
                except Exception as e:
                    results["failed_files"] += 1
                    results["file_results"][filename] = False
                    results["errors"].append(f"Error processing {filename}: {str(e)}")
            
            self.tracer.info(f"Batch processing completed: {results['successful_files']}/{results['total_files']} successful")
            return results
            
        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "Batch processing")
            return {"success": False, "error": str(e)}
    
    def auto_detect_and_process(self, input_path: str, output_path: str, **kwargs) -> bool:
        """
        Auto-detect file type and process accordingly
        
        Args:
            input_path: Input file path
            output_path: Output file path
        """
        try:
            # Detect file type
            file_ext = os.path.splitext(input_path)[1].lower()
            
            if file_ext in ['.yaml', '.yml']:
                return self.process_yaml_template(input_path, output_path, **kwargs)
            elif file_ext == '.json':
                return self.process_json_schema(input_path, output_path, **kwargs)
            else:
                self.tracer.error(f"Unsupported file type: {file_ext}")
                return False
                
        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "Auto-detect processing")
            return False
    
    def _update_mode_stats(self, mode: ProcessingMode):
        """Update statistics based on processing mode"""
        if mode in [ProcessingMode.HYBRID]:
            self.stats["hybrid_operations"] += 1
        elif mode in [ProcessingMode.AI_BASED, ProcessingMode.ML_ANALYSIS]:
            self.stats["ai_operations"] += 1
        elif mode in [ProcessingMode.RULE_BASED, ProcessingMode.DIRECT_PROCESSING]:
            self.stats["rule_operations"] += 1
    
    def _generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        return {
            "orchestrator_stats": self.stats,
            "yaml_service_summary": self.yaml_service.get_processing_summary(),
            "jsonschema_service_summary": self.jsonschema_service.get_processing_summary() if hasattr(self.jsonschema_service, 'get_processing_summary') else {},
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate processing recommendations based on statistics"""
        recommendations = []
        
        if self.stats["failed_operations"] > self.stats["successful_operations"] * 0.2:
            recommendations.append("High failure rate detected. Consider reviewing input data quality.")
        
        if self.stats["ai_operations"] > self.stats["rule_operations"]:
            recommendations.append("AI processing is being used frequently. Consider optimizing AI models.")
        
        if self.stats["hybrid_operations"] > 0:
            recommendations.append("Hybrid processing shows good balance between rule-based and AI approaches.")
        
        return recommendations
    
    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """Get comprehensive processing summary"""
        return {
            "orchestrator": {
                "product": self.product,
                "version": self.version,
                "stats": self.stats
            },
            "services": {
                "yaml_processing": self.yaml_service.get_processing_summary(),
                "jsonschema_processing": self.jsonschema_service.get_processing_summary() if hasattr(self.jsonschema_service, 'get_processing_summary') else {}
            },
            "recommendations": self._generate_recommendations()
        }