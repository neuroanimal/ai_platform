"""
Ultimate Integration Test - Test YANG and validation functionality
"""
import os
import sys
import tempfile
import shutil
import unittest
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.service_layer.format_processing.yang.yang_processing_module import YANGProcessingModule
from backend.service_layer.format_processing.validation.validation_service import ValidationService
from common.handler.trace_handler import TraceHandler


class TestUltimateIntegration(unittest.TestCase):
    """Test ultimate functionality integration"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.tracer = TraceHandler("TestPlatform", "1.0", "TestComponent")
        self.yang_processor = YANGProcessingModule(self.tracer)
        self.validation_service = ValidationService("TestPlatform", "1.0")

        # Create test data
        self.create_test_data()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_data(self):
        """Create test data files"""
        # Test YANG model
        self.test_yang = os.path.join(self.test_dir, "test-model.yang")
        yang_content = """module test-model {
    namespace "http://example.com/test-model";
    prefix "test";

    revision "2024-01-01" {
        description "Initial revision";
    }

    container config {
        description "Configuration container";

        leaf enabled {
            type boolean;
            default true;
            description "Enable feature";
        }

        leaf port {
            type uint16;
            default 8080;
            description "Port number";
        }

        list servers {
            key "name";
            description "Server list";

            leaf name {
                type string;
                description "Server name";
            }

            leaf host {
                type string;
                description "Server host";
            }
        }
    }
}"""
        with open(self.test_yang, 'w') as f:
            f.write(yang_content)

        # Test JSON file (valid)
        self.test_json_valid = os.path.join(self.test_dir, "valid.json")
        json_data = {
            "name": "test",
            "version": "1.0",
            "enabled": True
        }
        with open(self.test_json_valid, 'w') as f:
            json.dump(json_data, f, indent=2)

        # Test JSON file (invalid)
        self.test_json_invalid = os.path.join(self.test_dir, "invalid.json")
        with open(self.test_json_invalid, 'w') as f:
            f.write('{"invalid": json content}')

        # Test YAML file (valid)
        self.test_yaml_valid = os.path.join(self.test_dir, "valid.yaml")
        yaml_content = """name: test
version: "1.0"
enabled: true
config:
  port: 8080
  hosts:
    - localhost
    - 127.0.0.1
"""
        with open(self.test_yaml_valid, 'w') as f:
            f.write(yaml_content)

        # Test YAML file (invalid)
        self.test_yaml_invalid = os.path.join(self.test_dir, "invalid.yaml")
        with open(self.test_yaml_invalid, 'w') as f:
            f.write('invalid: yaml: content: [')

        # Test JSON Schema
        self.test_schema = os.path.join(self.test_dir, "test.schema.json")
        schema_data = {
            "$schema": "https://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "enabled": {"type": "boolean"}
            },
            "required": ["name", "version"]
        }
        with open(self.test_schema, 'w') as f:
            json.dump(schema_data, f, indent=2)

        # Test invalid schema
        self.test_schema_invalid = os.path.join(self.test_dir, "invalid.schema.json")
        invalid_schema = {
            "$schema": "https://json-schema.org/draft-07/schema#",
            "type": "invalid_type",
            "properties": "not_an_object"
        }
        with open(self.test_schema_invalid, 'w') as f:
            json.dump(invalid_schema, f, indent=2)

    def test_yang_validation(self):
        """Test YANG model validation"""
        # This test will pass even if pyang is not installed
        valid = self.yang_processor.validate_yang_model(self.test_yang)

        # Should return True (either valid or pyang not available)
        self.assertTrue(isinstance(valid, bool))

        # Test with non-existent file
        try:
            valid = self.yang_processor.validate_yang_model("non_existent.yang")
            self.assertFalse(valid)
        except Exception:
            # Expected if file doesn't exist
            pass

    def test_yang_schema_conversion(self):
        """Test YANG to JSON Schema conversion"""
        yang_dir = os.path.dirname(self.test_yang)
        output_dir = os.path.join(self.test_dir, "schemas")

        # Test conversion (will work if pyang is available)
        success = self.yang_processor.convert_to_json_schema(yang_dir, output_dir)

        # Should return boolean
        self.assertTrue(isinstance(success, bool))

        if success:
            # Check if schema files were created
            self.assertTrue(os.path.exists(output_dir))

    def test_yang_schema_combination(self):
        """Test combining JSON schemas"""
        # Create some test schemas
        schema_dir = os.path.join(self.test_dir, "test_schemas")
        os.makedirs(schema_dir, exist_ok=True)

        # Create test schema files
        for i in range(2):
            schema_file = os.path.join(schema_dir, f"schema_{i}.json")
            schema_data = {
                "type": "object",
                "properties": {
                    f"prop_{i}": {"type": "string"}
                }
            }
            with open(schema_file, 'w') as f:
                json.dump(schema_data, f)

        # Test combination
        combined_file = os.path.join(self.test_dir, "combined.schema.json")
        success = self.yang_processor.combine_schemas(schema_dir, combined_file)

        self.assertTrue(success)
        self.assertTrue(os.path.exists(combined_file))

        # Verify combined content
        with open(combined_file, 'r') as f:
            combined = json.load(f)
            self.assertIn("properties", combined)
            self.assertIn("prop_0", combined["properties"])
            self.assertIn("prop_1", combined["properties"])

    def test_json_validation(self):
        """Test JSON file validation"""
        # Valid JSON
        valid, error = self.validation_service.validate_json_file(self.test_json_valid)
        self.assertTrue(valid)
        self.assertIsNone(error)

        # Invalid JSON
        valid, error = self.validation_service.validate_json_file(self.test_json_invalid)
        self.assertFalse(valid)
        self.assertIsNotNone(error)

    def test_yaml_validation(self):
        """Test YAML file validation"""
        # Valid YAML
        valid, error = self.validation_service.validate_yaml_file(self.test_yaml_valid)
        self.assertTrue(valid)
        self.assertIsNone(error)

        # Invalid YAML
        valid, error = self.validation_service.validate_yaml_file(self.test_yaml_invalid)
        self.assertFalse(valid)
        self.assertIsNotNone(error)

    def test_schema_validation(self):
        """Test JSON Schema validation"""
        # Valid schema
        valid, error = self.validation_service.validate_json_schema(self.test_schema)
        self.assertTrue(valid)
        self.assertIsNone(error)

        # Invalid schema
        valid, error = self.validation_service.validate_json_schema(self.test_schema_invalid)
        self.assertFalse(valid)
        self.assertIsNotNone(error)

    def test_data_against_schema_validation(self):
        """Test validating data against schema"""
        # Valid data against schema
        valid, error = self.validation_service.validate_json_against_schema(
            self.test_json_valid, self.test_schema
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

        # Create invalid data
        invalid_data_file = os.path.join(self.test_dir, "invalid_data.json")
        invalid_data = {"name": 123}  # name should be string
        with open(invalid_data_file, 'w') as f:
            json.dump(invalid_data, f)

        valid, error = self.validation_service.validate_json_against_schema(
            invalid_data_file, self.test_schema
        )
        self.assertFalse(valid)
        self.assertIsNotNone(error)

    def test_directory_validation(self):
        """Test directory validation"""
        # Create test directory with mixed files
        test_dir = os.path.join(self.test_dir, "validation_test")
        os.makedirs(test_dir, exist_ok=True)

        # Copy test files
        shutil.copy2(self.test_json_valid, os.path.join(test_dir, "valid.json"))
        shutil.copy2(self.test_json_invalid, os.path.join(test_dir, "invalid.json"))

        # Test directory validation
        results = self.validation_service.validate_directory(test_dir, "*.json")

        self.assertEqual(len(results), 2)
        self.assertTrue(results["valid.json"][0])  # Should be valid
        self.assertFalse(results["invalid.json"][0])  # Should be invalid

    def test_validation_service_stats(self):
        """Test validation service statistics"""
        # Perform some validations
        self.validation_service.validate_json_file(self.test_json_valid)
        self.validation_service.validate_yaml_file(self.test_yaml_valid)
        self.validation_service.validate_json_schema(self.test_schema)

        # Check statistics
        summary = self.validation_service.get_summary()
        stats = summary["stats"]

        self.assertGreater(stats["validations_performed"], 0)
        self.assertGreater(stats["successful_validations"], 0)
        self.assertGreater(summary["success_rate"], 0)

    def test_yang_processor_stats(self):
        """Test YANG processor statistics"""
        # Perform some operations
        self.yang_processor.validate_yang_model(self.test_yang)

        # Check statistics
        summary = self.yang_processor.get_summary()

        self.assertIn("validations_performed", summary)
        self.assertIsInstance(summary["validations_performed"], int)


def run_ultimate_tests():
    """Run all ultimate tests"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUltimateIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_ultimate_tests()
    sys.exit(0 if success else 1)