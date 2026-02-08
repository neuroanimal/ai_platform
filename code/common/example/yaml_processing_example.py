#!/usr/bin/env python3
"""
Example usage of AI Platform YAML Processing
"""
import os
import sys
import tempfile

# Add AI Platform to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ai_platform.common.tool.yaml_uncommenter import YAMLUncommenter
from ai_platform.common.engine.yaml_processing_engine import YAMLProcessingEngine


def example_direct_usage():
    """Example of direct tool usage."""
    print("=== Direct Tool Usage ===")

    # Create sample YAML
    sample_yaml = """# Sample Kubernetes deployment
# apiVersion: apps/v1
# kind: Deployment
# metadata:
#   name: {{app_name|myapp}}
# spec:
#   replicas: {{replicas|1|3|5}}
#   selector:
#     matchLabels:
#       app: {{app_name|myapp}}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
        input_file.write(sample_yaml)
        input_file.flush()

        output_path = input_file.name.replace('.yaml', '_output.yaml')

        uncommenter = YAMLUncommenter()
        success = uncommenter.process(
            input_path=input_file.name,
            output_path=output_path,
            system_size='standard-system'
        )

        if success:
            print(f"✓ Processed successfully: {output_path}")
            with open(output_path, 'r') as f:
                print("Output:")
                print(f.read())
        else:
            print("✗ Processing failed")

        # Cleanup
        os.unlink(input_file.name)
        if os.path.exists(output_path):
            os.unlink(output_path)


def example_engine_usage():
    """Example of engine interface usage."""
    print("\n=== Engine Interface Usage ===")

    sample_yaml = """# Configuration template
# database:
#   host: {{db_host|localhost}}
#   port: {{db_port|5432|5433|5434}}
#   ssl: {{ssl_enabled|false|true|true}}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
        input_file.write(sample_yaml)
        input_file.flush()

        output_path = input_file.name.replace('.yaml', '_engine_output.yaml')

        engine = YAMLProcessingEngine()

        # Show capabilities
        caps = engine.get_capabilities()
        print(f"Engine: {caps['name']} v{caps['version']}")
        print(f"Supports: {', '.join(caps['supports'])}")

        # Process template
        result = engine.process_template(
            input_path=input_file.name,
            output_path=output_path,
            system_size='large-system'
        )

        if result['success']:
            print(f"✓ {result['message']}")
            with open(output_path, 'r') as f:
                print("Output:")
                print(f.read())
        else:
            print(f"✗ {result['message']}")

        # Cleanup
        os.unlink(input_file.name)
        if os.path.exists(output_path):
            os.unlink(output_path)


def main():
    """Run examples."""
    print("AI Platform YAML Processing Examples")
    print("=" * 50)

    example_direct_usage()
    example_engine_usage()

    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    main()