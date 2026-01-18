"""
Unified Processing Engine - Full Integration
Combines YAML and JSON Schema processing services into a single engine
"""
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from code.backend.service_layer.yaml_processing.yaml_processing_service import YAMLProcessingService
from code.backend.service_layer.schema_processing.jsonschema_processing_service import JSONSchemaProcessingService


class UnifiedProcessingEngine:
    """
    Unified processing engine combining YAML and JSON Schema processing.
    
    This engine provides a single interface for all document processing needs,
    integrating the full functionality of both uncomment-00 and jsonschema_reorder.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize service components
        self.yaml_service = YAMLProcessingService(self.config.get('yaml', {}))
        self.schema_service = JSONSchemaProcessingService(self.config.get('schema', {}))
    
    def process_yaml_template(self, input_path: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process YAML template with full uncomment-00 functionality.
        
        Args:
            input_path: Input YAML template file
            output_path: Output YAML file
            **kwargs: Processing options (mrcf_path, helm_path, system_size, etc.)
            
        Returns:
            Processing result with status and generated files
        """
        return self.yaml_service.process_yaml_template(input_path, output_path, **kwargs)
    
    def reorder_json_schema(self, schema_path: str, output_path: str, 
                           reference_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Reorder JSON Schema with full jsonschema_reorder functionality.
        
        Args:
            schema_path: Input JSON Schema file
            output_path: Output JSON Schema file
            reference_path: Reference file for ordering
            **kwargs: Processing options
            
        Returns:
            Processing result with reordered schema
        """
        return self.schema_service.reorder_from_files(
            schema_path=schema_path,
            reference_path=reference_path,
            output_path=output_path,
            **kwargs
        )
    
    def batch_process(self, files: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Batch process multiple files of different types.
        
        Args:
            files: List of file specifications with 'type', 'input', 'output' keys
            **kwargs: Global processing options
            
        Returns:
            Batch processing results
        """
        results = []
        successful = 0
        failed = 0
        
        for file_spec in files:
            try:
                file_type = file_spec.get('type', '').lower()
                input_path = file_spec['input']
                output_path = file_spec['output']
                
                if file_type in ['yaml', 'yml']:
                    result = self.process_yaml_template(input_path, output_path, **kwargs)
                elif file_type in ['json', 'jsonschema', 'schema']:
                    result = self.reorder_json_schema(
                        input_path, output_path, 
                        reference_path=file_spec.get('reference'), 
                        **kwargs
                    )
                else:
                    # Auto-detect by extension
                    ext = Path(input_path).suffix.lower()
                    if ext in ['.yaml', '.yml']:
                        result = self.process_yaml_template(input_path, output_path, **kwargs)
                    elif ext == '.json':
                        result = self.reorder_json_schema(
                            input_path, output_path,
                            reference_path=file_spec.get('reference'),
                            **kwargs
                        )
                    else:
                        raise ValueError(f"Unsupported file type: {ext}")
                
                results.append(result)
                if result.get('success', False):
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                    'file': file_spec,
                    'message': f'Processing failed: {e}'
                })
                failed += 1
        
        return {
            'success': failed == 0,
            'results': results,
            'total': len(files),
            'successful': successful,
            'failed': failed,
            'message': f'Processed {successful}/{len(files)} files successfully'
        }
    
    def validate_and_process(self, input_path: str, output_path: str, 
                           validation_config: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Validate and process files with comprehensive checks.
        
        Args:
            input_path: Input file path
            output_path: Output file path
            validation_config: Validation configuration
            **kwargs: Processing options
            
        Returns:
            Processing result with validation info
        """
        ext = Path(input_path).suffix.lower()
        
        try:
            if ext in ['.yaml', '.yml']:
                # Process YAML
                result = self.process_yaml_template(input_path, output_path, **kwargs)
                
                # Add YAML-specific validation if needed
                if validation_config and validation_config.get('validate_yaml', False):
                    # Could add YAML validation here
                    pass
                
            elif ext == '.json':
                # For JSON files, check if it's a schema
                with open(input_path, 'r') as f:
                    content = f.read()
                    if '"$schema"' in content or '"properties"' in content:
                        # Treat as JSON Schema
                        result = self.reorder_json_schema(input_path, output_path, **kwargs)
                        
                        # Add schema validation
                        if validation_config and validation_config.get('validate_schema', True):
                            import json
                            with open(input_path, 'r') as f:
                                schema = json.load(f)
                            validation_result = self.schema_service.validate_schema_structure(schema)
                            result['validation'] = validation_result
                    else:
                        # Regular JSON file - just format
                        import json
                        with open(input_path, 'r') as f:
                            data = json.load(f)
                        with open(output_path, 'w') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        result = {
                            'success': True,
                            'message': 'JSON file formatted successfully',
                            'input_path': input_path,
                            'output_path': output_path
                        }
            else:
                raise ValueError(f"Unsupported file extension: {ext}")
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'input_path': input_path,
                'message': f'Validation and processing failed: {e}'
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive engine capabilities."""
        return {
            'name': 'Unified Processing Engine',
            'version': '1.0.0',
            'services': {
                'yaml_processing': {
                    'name': 'YAML Processing Service',
                    'supports': [
                        'yaml_uncommenting',
                        'mrcf_integration', 
                        'helm_integration',
                        'multi_flavor_support',
                        'error_fixing',
                        'value_substitution',
                        'variant_generation'
                    ],
                    'flavors': ['small-system', 'standard-system', 'large-system'],
                    'formats': ['yaml', 'yml']
                },
                'schema_processing': {
                    'name': 'JSON Schema Processing Service',
                    'supports': [
                        'schema_reordering',
                        'keyword_sorting',
                        'reference_based_ordering',
                        'leaf_property_merging',
                        'batch_processing',
                        'schema_validation',
                        'complexity_analysis'
                    ],
                    'formats': ['json', 'yaml'],
                    'keywords': JSONSchemaProcessingService.SCHEMA_KEYWORD_ORDER
                }
            },
            'unified_features': [
                'batch_processing',
                'auto_detection',
                'validation_and_processing',
                'multi_format_support'
            ]
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and service status."""
        return {
            'yaml_service': {
                'mrcf_parameters_loaded': len(self.yaml_service.map_path_mrcf),
                'helm_values_loaded': len(self.yaml_service.map_path_helm),
                'config': self.yaml_service.config
            },
            'schema_service': {
                'config': self.schema_service.config,
                'supported_keywords': len(self.schema_service.SCHEMA_KEYWORD_ORDER),
                'leaf_blacklist_size': len(self.schema_service.LEAF_BLACKLIST)
            }
        }