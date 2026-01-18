"""
Enhanced Integration Test - Test Excel and conversion functionality
"""
import os
import sys
import tempfile
import shutil
import unittest
import pandas as pd
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.service_layer.format_processing.conversion.format_conversion_service import FormatConversionService
from common.engine.io_engine.excel_io_module import ExcelIOModule
from backend.service_layer.format_processing.json.json_schema_utilities import JSONSchemaUtilities
from common.handler.trace_handler import TraceHandler


class TestEnhancedIntegration(unittest.TestCase):
    """Test enhanced functionality integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.conversion_service = FormatConversionService("TestPlatform", "1.0")
        self.tracer = TraceHandler("TestPlatform", "1.0", "TestComponent")
        self.excel_io = ExcelIOModule(self.tracer)
        self.json_utils = JSONSchemaUtilities(self.tracer)
        
        # Create test data
        self.create_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_data(self):
        """Create test data files"""
        # Test JSON file
        self.test_json = os.path.join(self.test_dir, "test.json")
        json_data = {
            "name": "test",
            "version": "1.0",
            "config": {
                "enabled": True,
                "port": 8080,
                "hosts": ["localhost", "127.0.0.1"]
            }
        }
        with open(self.test_json, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Test YAML file
        self.test_yaml = os.path.join(self.test_dir, "test.yaml")
        yaml_content = """name: test
version: "1.0"
config:
  enabled: true
  port: 8080
  hosts:
    - localhost
    - 127.0.0.1
"""
        with open(self.test_yaml, 'w') as f:
            f.write(yaml_content)
        
        # Test Excel file
        self.test_excel = os.path.join(self.test_dir, "test.xlsx")
        data = {
            'Sheet1': pd.DataFrame({
                'Name': ['Alice', 'Bob', 'Charlie'],
                'Age': [25, 30, 35],
                'City': ['New York', 'London', 'Tokyo']
            }),
            'Sheet2': pd.DataFrame({
                'Product': ['A', 'B', 'C'],
                'Price': [10.0, 20.0, 30.0],
                'Stock': [100, 200, 300]
            })
        }
        self.excel_io.write_file(data, self.test_excel)
        
        # Test JSON Schema
        self.test_schema = os.path.join(self.test_dir, "test.schema.json")
        schema_data = {
            "$schema": "https://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "test"},
                "enabled": {"type": "boolean", "default": "true"},
                "port": {"type": "integer", "default": "8080"}
            },
            "required": ["name", "enabled", "missing_prop"]
        }
        with open(self.test_schema, 'w') as f:
            json.dump(schema_data, f, indent=2)
    
    def test_json_to_yaml_conversion(self):
        """Test JSON to YAML conversion"""
        output_path = os.path.join(self.test_dir, "converted.yaml")
        
        success = self.conversion_service.convert_file(
            self.test_json, output_path, "json", "yaml"
        )
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify content
        with open(output_path, 'r') as f:
            content = f.read()
            self.assertIn("name: test", content)
            self.assertIn("enabled: true", content)
    
    def test_yaml_to_json_conversion(self):
        """Test YAML to JSON conversion"""
        output_path = os.path.join(self.test_dir, "converted.json")
        
        success = self.conversion_service.convert_file(
            self.test_yaml, output_path, "yaml", "json"
        )
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify content
        with open(output_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["name"], "test")
            self.assertEqual(data["config"]["enabled"], True)
    
    def test_excel_table_extraction(self):
        """Test Excel table extraction"""
        output_dir = os.path.join(self.test_dir, "extracted")
        
        results = self.excel_io.extract_tables(self.test_excel, output_dir)
        
        self.assertGreater(len(results), 0)
        self.assertTrue(os.path.exists(output_dir))
        
        # Check that CSV files were created
        for sheet_name, csv_files in results.items():
            self.assertGreater(len(csv_files), 0)
            for csv_file in csv_files:
                self.assertTrue(os.path.exists(csv_file))
    
    def test_excel_validation(self):
        """Test Excel file validation"""
        # Valid Excel file
        valid = self.excel_io.validate_excel(self.test_excel)
        self.assertTrue(valid)
        
        # Invalid file
        invalid_file = os.path.join(self.test_dir, "invalid.xlsx")
        with open(invalid_file, 'w') as f:
            f.write("not an excel file")
        
        valid = self.excel_io.validate_excel(invalid_file)
        self.assertFalse(valid)
    
    def test_excel_sheet_names(self):
        """Test getting Excel sheet names"""
        sheet_names = self.excel_io.get_sheet_names(self.test_excel)
        
        self.assertIn('Sheet1', sheet_names)
        self.assertIn('Sheet2', sheet_names)
        self.assertEqual(len(sheet_names), 2)
    
    def test_json_schema_utilities(self):
        """Test JSON Schema utilities"""
        # Load schema
        with open(self.test_schema, 'r') as f:
            schema = json.load(f)
        
        # Process schema
        processed_schema = self.json_utils.process_schema(schema)
        
        # Check that additionalProperties was added
        self.assertTrue(processed_schema.get("additionalProperties", False))
        
        # Check that type inconsistencies were fixed
        self.assertEqual(processed_schema["properties"]["enabled"]["default"], True)
        self.assertEqual(processed_schema["properties"]["port"]["default"], 8080)
        
        # Check that dead required was cleaned
        required = processed_schema.get("required", [])
        self.assertNotIn("missing_prop", required)
    
    def test_conversion_service_stats(self):
        """Test conversion service statistics"""
        # Perform some conversions
        output1 = os.path.join(self.test_dir, "out1.yaml")
        output2 = os.path.join(self.test_dir, "out2.json")
        
        self.conversion_service.convert_file(self.test_json, output1)
        self.conversion_service.convert_file(self.test_yaml, output2)
        
        # Check statistics
        summary = self.conversion_service.get_summary()
        stats = summary["stats"]
        
        self.assertGreater(stats["conversions_performed"], 0)
        self.assertGreater(stats["json_to_yaml"], 0)
        self.assertGreater(stats["yaml_to_json"], 0)
    
    def test_excel_io_stats(self):
        """Test Excel IO statistics"""
        # Perform some operations
        self.excel_io.read_file(self.test_excel)
        output_dir = os.path.join(self.test_dir, "stats_test")
        self.excel_io.extract_tables(self.test_excel, output_dir)
        
        # Check statistics
        summary = self.excel_io.get_summary()
        
        self.assertGreater(summary["files_read"], 0)
        self.assertGreater(summary["sheets_processed"], 0)
        self.assertGreater(summary["tables_extracted"], 0)
    
    def test_json_schema_utilities_stats(self):
        """Test JSON Schema utilities statistics"""
        # Load and process schema
        with open(self.test_schema, 'r') as f:
            schema = json.load(f)
        
        self.json_utils.process_schema(schema)
        
        # Check statistics
        summary = self.json_utils.get_summary()
        
        self.assertGreater(summary["schemas_processed"], 0)
        self.assertGreater(summary["types_fixed"], 0)
        self.assertGreater(summary["required_cleaned"], 0)


def run_enhanced_tests():
    """Run all enhanced tests"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEnhancedIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_enhanced_tests()
    sys.exit(0 if success else 1)