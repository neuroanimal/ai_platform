#!/usr/bin/env python3
"""
Uncomment CLI Tool - Direct access to YAML processing functionality
"""
import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.trace_handler import TraceHandler
from engines.orchestrator_engine_v2 import OrchestratorEngine


def main():
    parser = argparse.ArgumentParser(description='YAML Uncommenting Tool')
    parser.add_argument('input_file', help='Input YAML template file')
    parser.add_argument('--product', default='CLI', help='Product name')
    parser.add_argument('--version', default='1.0', help='Version')
    parser.add_argument('--mrcf', help='MRCF JSON file path')
    parser.add_argument('--helm', help='Helm charts folder path')
    parser.add_argument('--flavor', default='standard-system',
                       choices=['small-system', 'standard-system', 'large-system'],
                       help='System size flavor')
    parser.add_argument('--mode', default='direct',
                       choices=['ml', 'direct', 'hybrid'],
                       help='Processing mode')
    parser.add_argument('--output', help='Output file path')

    args = parser.parse_args()

    # Initialize orchestrator
    config = {}
    orchestrator = OrchestratorEngine(args.product, args.version, config)

    # Set up paths if using CLI mode
    if args.output:
        # Create a temporary data structure for CLI usage
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        data_dir = os.path.join(temp_dir, 'data', args.product, args.version)
        os.makedirs(os.path.join(data_dir, 'input', 'template'), exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'output', 'template'), exist_ok=True)

        # Copy input file
        input_template = os.path.join(data_dir, 'input', 'template', 'values.yaml')
        shutil.copy2(args.input_file, input_template)

        # Update orchestrator paths
        orchestrator.product = args.product
        orchestrator.version = args.version

        try:
            if args.mode == 'ml':
                success = orchestrator.run_uncomment_process()
                output_file = os.path.join(data_dir, 'output', 'template', 'uncommented_values.yaml')
            elif args.mode == 'direct':
                success = orchestrator.run_direct_yaml_process(
                    mrcf_path=args.mrcf,
                    helm_path=args.helm,
                    system_size=args.flavor
                )
                output_file = os.path.join(data_dir, 'output', 'template', 'uncommented_values_direct.yaml')
            else:  # hybrid
                success = orchestrator.run_hybrid_process(
                    mrcf_path=args.mrcf,
                    helm_path=args.helm,
                    system_size=args.flavor
                )
                output_file = os.path.join(data_dir, 'output', 'template', 'uncommented_values_hybrid.yaml')

            if success and os.path.exists(output_file):
                shutil.copy2(output_file, args.output)
                print(f"Successfully processed: {args.output}")
            else:
                print("Processing failed")
                sys.exit(1)

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        # Use existing data structure
        if args.mode == 'ml':
            orchestrator.run_uncomment_process()
        elif args.mode == 'direct':
            orchestrator.run_direct_yaml_process(
                mrcf_path=args.mrcf,
                helm_path=args.helm,
                system_size=args.flavor
            )
        else:  # hybrid
            orchestrator.run_hybrid_process(
                mrcf_path=args.mrcf,
                helm_path=args.helm,
                system_size=args.flavor
            )


if __name__ == "__main__":
    main()