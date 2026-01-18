"""
Comprehensive Test Suite for Full Integration
Tests all functionality from both uncomment-00 and jsonschema_reorder
"""
import os
import json
import tempfile
import unittest
from pathlib import Path

from code.backend.service_layer.yaml_processing.yaml_processing_service import YAMLProcessingService
from code.backend.service_layer.schema_processing.jsonschema_processing_service import JSONSchemaProcessingService
from code.common.engine.unified_processing_engine import UnifiedProcessingEngine


class TestFullIntegration(unittest.TestCase):
    """Comprehensive test suite for full integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.yaml_service = YAMLProcessingService()
        self.schema_service = JSONSchemaProcessingService()
        self.unified_engine = UnifiedProcessingEngine()
        
        # Test YAML template
        self.test_yaml = """# Test YAML template with various features
# global:
#   imageRegistry: "{{registry_url|default.registry.com|prod.registry.com|enterprise.registry.com}}"
#   storageClass: "{{storage_class|fast|standard|slow}}"
#   debug: {{debug_enabled|false|true|true}}
# 
# app:
#   name: "{{app_name|myapp}}"
#   replicas: {{replicas|1|3|5}}
#   resources:
#     requests:
#       memory: "{{memory_request|128Mi|256Mi|512Mi}}"
#       cpu: "{{cpu_request|100m|200m|400m}}"
#   # This is a complex nested structure
#   config:
#     database:
#       host: "{{db_host|localhost}}"
#       port: {{db_port|5432|5433|5434}}
#       ssl: {{ssl_enabled|false|true|true}}
"""
        
        # Test JSON Schema (unordered)
        self.test_schema = {
            "additionalProperties": False,
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "User email address"
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "User full name"
                },
                "age": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 150
                },
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "country": {"type": "string"}
                    },
                    "required": ["street", "city"]
                }
            },
            "required": ["name", "email"],
            "type": "object",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "https://example.com/person.schema.json",
            "title": "Person Schema",
            "description": "Schema for person data"
        }
        
        # Reference schema for ordering
        self.reference_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "https://example.com/person.schema.json",
            "title": "Person Schema",
            "description": "Schema for person data",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"},
                "address": {"type": "object"}
            },
            "required": ["name", "email"],
            "additionalProperties": False
        }
    
    def test_yaml_service_full_processing(self):
        """Test complete YAML processing functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write(self.test_yaml)
            input_file.flush()
            
            output_path = input_file.name.replace('.yaml', '_processed.yaml')
            
            result = self.yaml_service.process_yaml_template(
                input_path=input_file.name,
                output_path=output_path,
                system_size='standard-system',
                generate_variants=True
            )
            
            self.assertTrue(result['success'])
            self.assertIn('files_generated', result)
            self.assertGreater(len(result['files_generated']), 0)
            
            # Check main output file exists
            self.assertTrue(os.path.exists(output_path))
            
            # Check content was processed
            with open(output_path, 'r') as f:
                processed_content = f.read()
                self.assertIn('global:', processed_content)
                self.assertIn('imageRegistry:', processed_content)
                # Should have uncommented the YAML
                self.assertNotIn('# global:', processed_content)
            
            # Cleanup
            for file_path in result['files_generated']:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            os.unlink(input_file.name)
    
    def test_schema_service_full_processing(self):
        """Test complete JSON Schema processing functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump(self.test_schema, schema_file, indent=2)
            schema_file.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as ref_file:
                json.dump(self.reference_schema, ref_file, indent=2)
                ref_file.flush()
                
                output_path = schema_file.name.replace('.json', '_reordered.json')
                
                result = self.schema_service.reorder_from_files(
                    schema_path=schema_file.name,
                    reference_path=ref_file.name,
                    output_path=output_path,
                    sort_keywords=True,
                    merge_leaf_properties=False
                )
                
                self.assertTrue(result['success'])
                self.assertTrue(os.path.exists(output_path))
                
                # Check reordering
                with open(output_path, 'r') as f:
                    reordered = json.load(f)
                    keys = list(reordered.keys())
                    
                    # $schema should be first
                    self.assertEqual(keys[0], '$schema')
                    # additionalProperties should be last
                    self.assertEqual(keys[-1], 'additionalProperties')
                    
                    # Properties should follow reference order
                    props = reordered['properties']
                    prop_keys = list(props.keys())
                    ref_props = list(self.reference_schema['properties'].keys())
                    
                    # Check that reference order is respected
                    for i, ref_key in enumerate(ref_props):
                        if ref_key in prop_keys:
                            self.assertEqual(prop_keys[prop_keys.index(ref_key)], ref_key)
                
                # Cleanup
                os.unlink(schema_file.name)
                os.unlink(ref_file.name)
                os.unlink(output_path)
    
    def test_schema_validation_and_analysis(self):
        """Test schema validation and analysis features."""
        # Test validation
        validation = self.schema_service.validate_schema_structure(self.test_schema)
        self.assertIn('valid', validation)
        self.assertIn('issues', validation)
        self.assertIn('recommendations', validation)
        
        # Test schema info
        info = self.schema_service.get_schema_info(self.test_schema)
        self.assertEqual(info['type'], 'object')
        self.assertTrue(info['has_properties'])
        self.assertEqual(info['property_count'], 4)
        self.assertIn('name', info['property_names'])
        self.assertGreater(info['complexity'], 0)
    
    def test_unified_engine_yaml_processing(self):
        """Test unified engine YAML processing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write(self.test_yaml)
            input_file.flush()
            
            output_path = input_file.name.replace('.yaml', '_unified.yaml')
            
            result = self.unified_engine.process_yaml_template(
                input_path=input_file.name,
                output_path=output_path,
                system_size='large-system'
            )
            
            self.assertTrue(result['success'])
            self.assertTrue(os.path.exists(output_path))
            
            # Cleanup
            for file_path in result.get('files_generated', []):
                if os.path.exists(file_path):
                    os.unlink(file_path)
            os.unlink(input_file.name)
    
    def test_unified_engine_schema_processing(self):
        """Test unified engine schema processing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump(self.test_schema, schema_file, indent=2)
            schema_file.flush()
            
            output_path = schema_file.name.replace('.json', '_unified.json')
            
            result = self.unified_engine.reorder_json_schema(
                schema_path=schema_file.name,
                output_path=output_path,
                sort_keywords=True
            )
            
            self.assertTrue(result['success'])
            self.assertTrue(os.path.exists(output_path))
            
            # Cleanup
            os.unlink(schema_file.name)
            os.unlink(output_path)
    
    def test_batch_processing(self):
        """Test batch processing functionality."""
        # Create test files
        yaml_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml_file.write(self.test_yaml)
        yaml_file.close()
        
        schema_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_schema, schema_file, indent=2)
        schema_file.close()
        
        # Define batch job
        files = [
            {
                'type': 'yaml',
                'input': yaml_file.name,
                'output': yaml_file.name.replace('.yaml', '_batch.yaml')
            },
            {
                'type': 'json',
                'input': schema_file.name,
                'output': schema_file.name.replace('.json', '_batch.json')
            }
        ]
        
        result = self.unified_engine.batch_process(files, system_size='standard-system')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['successful'], 2)
        self.assertEqual(result['failed'], 0)
        
        # Cleanup
        os.unlink(yaml_file.name)
        os.unlink(schema_file.name)
        for file_spec in files:
            if os.path.exists(file_spec['output']):
                os.unlink(file_spec['output'])
    
    def test_auto_detection_processing(self):
        """Test auto-detection and processing."""
        # Test YAML auto-detection
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_file:
            yaml_file.write(self.test_yaml)
            yaml_file.flush()
            
            yaml_output = yaml_file.name.replace('.yaml', '_auto.yaml')
            
            result = self.unified_engine.validate_and_process(
                input_path=yaml_file.name,
                output_path=yaml_output
            )
            
            self.assertTrue(result['success'])
            
            # Cleanup
            os.unlink(yaml_file.name)
            if os.path.exists(yaml_output):
                os.unlink(yaml_output)
        
        # Test JSON Schema auto-detection
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump(self.test_schema, schema_file, indent=2)
            schema_file.flush()
            
            schema_output = schema_file.name.replace('.json', '_auto.json')
            
            result = self.unified_engine.validate_and_process(
                input_path=schema_file.name,
                output_path=schema_output,
                validation_config={'validate_schema': True}
            )
            
            self.assertTrue(result['success'])
            self.assertIn('validation', result)
            
            # Cleanup
            os.unlink(schema_file.name)
            if os.path.exists(schema_output):
                os.unlink(schema_output)
    
    def test_engine_capabilities(self):
        """Test engine capabilities reporting."""
        caps = self.unified_engine.get_capabilities()
        
        self.assertEqual(caps['name'], 'Unified Processing Engine')
        self.assertIn('services', caps)
        self.assertIn('yaml_processing', caps['services'])
        self.assertIn('schema_processing', caps['services'])
        self.assertIn('unified_features', caps)
        
        # Test stats
        stats = self.unified_engine.get_processing_stats()
        self.assertIn('yaml_service', stats)
        self.assertIn('schema_service', stats)
    
    def test_complex_yaml_scenarios(self):
        """Test complex YAML processing scenarios."""
        complex_yaml = """# Complex YAML with edge cases
# global:
#   # Nested comments
#   registry:
#     # Multiple levels
#     url: "{{registry_url|default.com}}"
#     # Array with placeholders
#     mirrors:
#       # - "{{mirror1|mirror1.com}}"
#       # - "{{mirror2|mirror2.com}}"
#   # Empty objects and arrays
#   # emptyObj: {}
#   # emptyArray: []
# 
# # JSON-like content in comments
# # {
# #   "key": "value",
# #   "nested": {
# #     "prop": "{{placeholder|default}}"
# #   }
# # }
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write(complex_yaml)
            input_file.flush()
            
            output_path = input_file.name.replace('.yaml', '_complex.yaml')
            
            result = self.yaml_service.process_yaml_template(
                input_path=input_file.name,
                output_path=output_path,
                system_size='standard-system'
            )
            
            # Should handle complex scenarios without crashing
            self.assertTrue(result['success'])
            
            # Cleanup
            for file_path in result.get('files_generated', []):
                if os.path.exists(file_path):
                    os.unlink(file_path)
            os.unlink(input_file.name)
    
    def test_complex_schema_scenarios(self):
        """Test complex JSON Schema processing scenarios."""
        complex_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "https://example.com/complex.schema.json",
            "title": "Complex Schema",
            "type": "object",
            "allOf": [
                {"properties": {"base": {"type": "string"}}},
                {"properties": {"extended": {"type": "number"}}}
            ],
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {
                        "deep": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            },
            "patternProperties": {
                "^[a-z]+$": {"type": "string"}
            },
            "additionalProperties": False,
            "if": {"properties": {"type": {"const": "special"}}},
            "then": {"required": ["specialField"]},
            "else": {"required": ["normalField"]}
        }
        
        # Test reordering complex schema
        result = self.schema_service.reorder_schema(complex_schema)
        
        # Should handle complex schemas
        self.assertIsInstance(result, dict)
        self.assertIn('$schema', result)
        self.assertIn('properties', result)
        
        # Test validation
        validation = self.schema_service.validate_schema_structure(complex_schema)
        self.assertIn('valid', validation)
        
        # Test complexity calculation
        info = self.schema_service.get_schema_info(complex_schema)
        self.assertGreater(info['complexity'], 10)  # Should be complex


if __name__ == '__main__':
    unittest.main()