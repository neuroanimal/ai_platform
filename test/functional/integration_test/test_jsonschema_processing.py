"""
Test for AI Platform JSON Schema Processing Integration
"""
import os
import json
import tempfile
import unittest
from code.common.tool.jsonschema_reorder import JSONSchemaReorder
from code.common.engine.jsonschema_processing_engine import JSONSchemaProcessingEngine


class TestJSONSchemaProcessing(unittest.TestCase):
    """Test JSON Schema processing functionality."""

    def setUp(self):
        self.reorder = JSONSchemaReorder()
        self.engine = JSONSchemaProcessingEngine()

        # Test schema
        self.test_schema = {
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"],
            "type": "object",
            "$schema": "http://json-schema.org/draft-07/schema#"
        }

        # Reference schema for ordering
        self.reference_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
                "name": {"type": "string"}
            },
            "required": ["name"],
            "additionalProperties": False
        }

    def test_basic_reordering(self):
        """Test basic schema reordering."""
        result = self.reorder.reorder(self.test_schema)

        # Check that $schema comes first
        keys = list(result.keys())
        self.assertEqual(keys[0], "$schema")

        # Check that additionalProperties comes last
        self.assertEqual(keys[-1], "additionalProperties")

    def test_reference_based_reordering(self):
        """Test reordering with reference."""
        result = self.reorder.reorder(self.test_schema, self.reference_schema)

        # Check property order follows reference
        props = result["properties"]
        prop_keys = list(props.keys())
        self.assertEqual(prop_keys[0], "age")  # age first in reference
        self.assertEqual(prop_keys[1], "name")  # name second in reference

    def test_file_processing(self):
        """Test file-based processing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump(self.test_schema, schema_file)
            schema_file.flush()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as ref_file:
                json.dump(self.reference_schema, ref_file)
                ref_file.flush()

                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
                    result = self.reorder.reorder_from_files(
                        schema_path=schema_file.name,
                        reference_path=ref_file.name,
                        output_path=output_file.name
                    )

                    # Check result
                    self.assertIn("$schema", result)
                    self.assertIn("properties", result)

                    # Check output file was created
                    self.assertTrue(os.path.exists(output_file.name))

                    # Cleanup
                    os.unlink(schema_file.name)
                    os.unlink(ref_file.name)
                    os.unlink(output_file.name)

    def test_engine_interface(self):
        """Test engine interface."""
        result = self.engine.reorder_schema(self.test_schema, self.reference_schema)

        self.assertTrue(result['success'])
        self.assertIn('result', result)
        self.assertIn('Schema reordered', result['message'])

        # Check reordered schema
        reordered = result['result']
        keys = list(reordered.keys())
        self.assertEqual(keys[0], "$schema")

    def test_engine_file_processing(self):
        """Test engine file processing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump(self.test_schema, schema_file)
            schema_file.flush()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
                result = self.engine.reorder_from_files(
                    schema_path=schema_file.name,
                    output_path=output_file.name
                )

                self.assertTrue(result['success'])
                self.assertIn('processed successfully', result['message'])

                # Cleanup
                os.unlink(schema_file.name)
                os.unlink(output_file.name)

    def test_capabilities(self):
        """Test engine capabilities."""
        caps = self.engine.get_capabilities()
        self.assertEqual(caps['name'], 'JSON Schema Processing Engine')
        self.assertIn('schema_reordering', caps['supports'])
        self.assertIn('json', caps['formats'])
        self.assertIn('$schema', caps['keywords'])


if __name__ == '__main__':
    unittest.main()