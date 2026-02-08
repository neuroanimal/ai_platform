"""
Test for AI Platform YAML Processing Integration
"""
import os
import tempfile
import unittest
from code.common.tool.yaml_uncommenter import YAMLUncommenter
from code.common.engine.yaml_processing_engine import YAMLProcessingEngine


class TestYAMLProcessing(unittest.TestCase):
    """Test YAML processing functionality."""

    def setUp(self):
        self.uncommenter = YAMLUncommenter()
        self.engine = YAMLProcessingEngine()

        # Create test YAML content
        self.test_yaml = """# Test YAML template
# global:
#   imageRegistry: "{{registry_url|default.registry.com}}"
#   storageClass: "{{storage_class|fast|standard|slow}}"
#
# app:
#   replicas: {{replicas|1|3|5}}
#   enabled: true
"""

    def test_basic_uncommenting(self):
        """Test basic uncommenting functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write(self.test_yaml)
            input_file.flush()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as output_file:
                success = self.uncommenter.process(
                    input_path=input_file.name,
                    output_path=output_file.name,
                    system_size='standard-system'
                )

                self.assertTrue(success)

                # Check output
                with open(output_file.name, 'r') as f:
                    result = f.read()
                    self.assertIn('global:', result)
                    self.assertIn('imageRegistry:', result)

                # Cleanup
                os.unlink(input_file.name)
                os.unlink(output_file.name)

    def test_engine_interface(self):
        """Test engine interface."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write(self.test_yaml)
            input_file.flush()

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as output_file:
                result = self.engine.process_template(
                    input_path=input_file.name,
                    output_path=output_file.name,
                    system_size='large-system'
                )

                self.assertTrue(result['success'])
                self.assertIn('completed', result['message'])

                # Cleanup
                os.unlink(input_file.name)
                os.unlink(output_file.name)

    def test_capabilities(self):
        """Test engine capabilities."""
        caps = self.engine.get_capabilities()
        self.assertEqual(caps['name'], 'YAML Processing Engine')
        self.assertIn('yaml_uncommenting', caps['supports'])
        self.assertIn('standard-system', caps['flavors'])


if __name__ == '__main__':
    unittest.main()