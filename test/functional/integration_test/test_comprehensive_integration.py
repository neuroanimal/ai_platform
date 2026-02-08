"""
Comprehensive Integration Test - Test all integrated functionality
Tests the complete integration of uncomment project into AI Platform
"""
import os
import sys
import tempfile
import shutil
import unittest
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.engine.unified_orchestrator_engine import UnifiedOrchestratorEngine, ProcessingMode
from backend.service_layer.format_processing.yaml.yaml_processing_service import YAMLProcessingService
from common.handler.trace_handler import TraceHandler


class TestComprehensiveIntegration(unittest.TestCase):
    """Comprehensive integration tests for AI Platform"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.orchestrator = UnifiedOrchestratorEngine("TestPlatform", "1.0")
        self.yaml_service = YAMLProcessingService("TestPlatform", "1.0")

        # Create test data
        self.create_test_data()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_data(self):
        """Create test data files"""
        # Test YAML template
        self.test_yaml = os.path.join(self.test_dir, "test_template.yaml")
        yaml_content = """# Test YAML Template
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  # enabled: true
  # port: 8080
  # host: localhost
  # database:
  #   name: testdb
  #   user: testuser
  #   password: secret
  active_setting: value
"""
        with open(self.test_yaml, 'w') as f:
            f.write(yaml_content)

        # Test MRCF file
        self.test_mrcf = os.path.join(self.test_dir, "test_mrcf.json")
        mrcf_content = {
            "parameters": [
                {
                    "path": "enabled",
                    "name": "enabled",
                    "format": "boolean",
                    "mandatory": "yes",
                    "description": "Enable feature"
                },
                {
                    "path": "port",
                    "name": "port",
                    "format": "integer",
                    "mandatory": "no",
                    "description": "Port number"
                },
                {
                    "path": "database.name",
                    "name": "database.name",
                    "format": "string",
                    "mandatory": "yes",
                    "description": "Database name"
                }
            ],
            "enabled": True,
            "port": 8080,
            "database": {
                "name": "testdb",
                "user": "testuser"
            }
        }

        import json
        with open(self.test_mrcf, 'w') as f:
            json.dump(mrcf_content, f, indent=2)

        # Test Helm directory structure
        self.test_helm_dir = os.path.join(self.test_dir, "helm")
        os.makedirs(self.test_helm_dir, exist_ok=True)

        # Create a simple values.yaml in helm directory
        helm_values = os.path.join(self.test_helm_dir, "values.yaml")
        helm_content = """enabled: true
port: 8080
host: localhost
database:
  name: proddb
  user: produser
"""
        with open(helm_values, 'w') as f:
            f.write(helm_content)

    def test_yaml_service_initialization(self):
        """Test YAML service initialization"""
        self.assertIsNotNone(self.yaml_service)
        self.assertEqual(self.yaml_service.product, "TestPlatform")
        self.assertEqual(self.yaml_service.version, "1.0")

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        self.assertIsNotNone(self.orchestrator)
        self.assertEqual(self.orchestrator.product, "TestPlatform")
        self.assertEqual(self.orchestrator.version, "1.0")

    def test_yaml_rule_based_processing(self):
        """Test rule-based YAML processing"""
        output_path = os.path.join(self.test_dir, "rule_output.yaml")

        success = self.orchestrator.process_yaml_template(
            input_path=self.test_yaml,
            output_path=output_path,
            mode=ProcessingMode.RULE_BASED,
            mrcf_path=self.test_mrcf,
            helm_path=self.test_helm_dir
        )

        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))

        # Verify some content was processed
        with open(output_path, 'r') as f:
            content = f.read()
            self.assertIn("apiVersion: v1", content)

    def test_yaml_ai_based_processing(self):
        """Test AI-based YAML processing"""
        output_path = os.path.join(self.test_dir, "ai_output.yaml")

        success = self.orchestrator.process_yaml_template(
            input_path=self.test_yaml,
            output_path=output_path,
            mode=ProcessingMode.AI_BASED,
            mrcf_path=self.test_mrcf,
            helm_path=self.test_helm_dir
        )

        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))

    def test_yaml_hybrid_processing(self):
        """Test hybrid YAML processing"""
        output_path = os.path.join(self.test_dir, "hybrid_output.yaml")

        success = self.orchestrator.process_yaml_template(
            input_path=self.test_yaml,
            output_path=output_path,
            mode=ProcessingMode.HYBRID,
            mrcf_path=self.test_mrcf,
            helm_path=self.test_helm_dir
        )

        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))

    def test_ml_analysis_workflow(self):
        """Test ML analysis workflow"""
        output_dir = os.path.join(self.test_dir, "ml_analysis")

        results = self.orchestrator.run_ml_analysis_workflow(
            input_path=self.test_yaml,
            output_dir=output_dir,
            mrcf_path=self.test_mrcf,
            helm_path=self.test_helm_dir
        )

        self.assertTrue(results["success"])
        self.assertTrue(os.path.exists(output_dir))
        self.assertIn("outputs", results)
        self.assertIn("analysis", results)

    def test_batch_processing(self):
        """Test batch processing"""
        # Create multiple test files
        batch_input_dir = os.path.join(self.test_dir, "batch_input")
        batch_output_dir = os.path.join(self.test_dir, "batch_output")
        os.makedirs(batch_input_dir, exist_ok=True)

        # Copy test file multiple times
        for i in range(3):
            shutil.copy2(self.test_yaml, os.path.join(batch_input_dir, f"test_{i}.yaml"))

        results = self.orchestrator.run_batch_processing(
            input_dir=batch_input_dir,
            output_dir=batch_output_dir,
            file_pattern="*.yaml",
            mode=ProcessingMode.HYBRID,
            mrcf_path=self.test_mrcf,
            helm_path=self.test_helm_dir
        )

        self.assertEqual(results["total_files"], 3)
        self.assertTrue(results["successful_files"] > 0)
        self.assertTrue(os.path.exists(batch_output_dir))

    def test_auto_detect_processing(self):
        """Test auto-detect processing"""
        output_path = os.path.join(self.test_dir, "auto_output.yaml")

        success = self.orchestrator.auto_detect_and_process(
            input_path=self.test_yaml,
            output_path=output_path,
            mode=ProcessingMode.HYBRID,
            mrcf_path=self.test_mrcf,
            helm_path=self.test_helm_dir
        )

        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))

    def test_yaml_validation(self):
        """Test YAML validation"""
        valid = self.yaml_service.validate_yaml_syntax(self.test_yaml)
        self.assertTrue(valid)

        # Test invalid YAML
        invalid_yaml = os.path.join(self.test_dir, "invalid.yaml")
        with open(invalid_yaml, 'w') as f:
            f.write("invalid: yaml: content: [")

        valid = self.yaml_service.validate_yaml_syntax(invalid_yaml)
        self.assertFalse(valid)

    def test_processing_statistics(self):
        """Test processing statistics collection"""
        output_path = os.path.join(self.test_dir, "stats_output.yaml")

        # Process a file
        self.orchestrator.process_yaml_template(
            input_path=self.test_yaml,
            output_path=output_path,
            mode=ProcessingMode.HYBRID,
            mrcf_path=self.test_mrcf
        )

        # Check statistics
        summary = self.orchestrator.get_comprehensive_summary()

        self.assertIn("orchestrator", summary)
        self.assertIn("services", summary)
        self.assertIn("recommendations", summary)

        # Verify some operations were recorded
        stats = summary["orchestrator"]["stats"]
        self.assertGreater(stats["total_operations"], 0)
        self.assertGreater(stats["successful_operations"], 0)

    def test_error_handling(self):
        """Test error handling"""
        # Test with non-existent input file
        output_path = os.path.join(self.test_dir, "error_output.yaml")

        success = self.orchestrator.process_yaml_template(
            input_path="/non/existent/file.yaml",
            output_path=output_path,
            mode=ProcessingMode.HYBRID
        )

        self.assertFalse(success)

        # Verify error was recorded in statistics
        stats = self.orchestrator.stats
        self.assertGreater(stats["failed_operations"], 0)

    def test_component_integration(self):
        """Test integration between components"""
        # Test that all components can work together
        output_path = os.path.join(self.test_dir, "integration_output.yaml")

        success = self.orchestrator.process_yaml_template(
            input_path=self.test_yaml,
            output_path=output_path,
            mode=ProcessingMode.HYBRID,
            mrcf_path=self.test_mrcf,
            helm_path=self.test_helm_dir
        )

        self.assertTrue(success)

        # Get summaries from all components
        yaml_summary = self.yaml_service.get_processing_summary()
        orchestrator_summary = self.orchestrator.get_comprehensive_summary()

        # Verify components have processed data
        self.assertIn("stats", yaml_summary)
        self.assertIn("components", yaml_summary)
        self.assertIn("orchestrator", orchestrator_summary)
        self.assertIn("services", orchestrator_summary)

    def test_different_system_sizes(self):
        """Test processing with different system sizes"""
        for system_size in ["small-system", "standard-system", "large-system"]:
            output_path = os.path.join(self.test_dir, f"{system_size}_output.yaml")

            success = self.orchestrator.process_yaml_template(
                input_path=self.test_yaml,
                output_path=output_path,
                mode=ProcessingMode.HYBRID,
                mrcf_path=self.test_mrcf,
                helm_path=self.test_helm_dir,
                system_size=system_size
            )

            self.assertTrue(success, f"Failed for system size: {system_size}")
            self.assertTrue(os.path.exists(output_path))


class TestTraceHandler(unittest.TestCase):
    """Test trace handler functionality"""

    def test_trace_handler_initialization(self):
        """Test trace handler initialization"""
        tracer = TraceHandler("TestProduct", "1.0", "TestComponent")

        self.assertEqual(tracer.product, "TestProduct")
        self.assertEqual(tracer.version, "1.0")
        self.assertEqual(tracer.component, "TestComponent")

    def test_logging_methods(self):
        """Test logging methods"""
        tracer = TraceHandler("TestProduct", "1.0", "TestComponent")

        tracer.info("Test info message")
        tracer.warning("Test warning message")
        tracer.error("Test error message")
        tracer.debug("Test debug message")

        # Check statistics
        stats = tracer.get_summary()
        self.assertGreater(stats["stats"]["info"], 0)
        self.assertGreater(stats["stats"]["warning"], 0)
        self.assertGreater(stats["stats"]["error"], 0)

    def test_decision_tracking(self):
        """Test decision tracking"""
        tracer = TraceHandler("TestProduct", "1.0", "TestComponent")

        tracer.trace_decision("test_step", "test_reason", {"key": "value"})

        summary = tracer.get_summary()
        self.assertGreater(summary["decisions_count"], 0)


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    # Create test suite
    suite = unittest.TestSuite()

    # Add integration tests
    suite.addTest(unittest.makeSuite(TestComprehensiveIntegration))
    suite.addTest(unittest.makeSuite(TestTraceHandler))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)