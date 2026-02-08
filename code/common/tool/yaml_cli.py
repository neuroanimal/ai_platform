#!/usr/bin/env python3
"""
AI Platform YAML Uncommenter CLI
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from code.common.tool.yaml_uncommenter import YAMLUncommenter


def main():
    parser = argparse.ArgumentParser(description='AI Platform YAML Uncommenter')
    parser.add_argument('input', help='Input YAML file')
    parser.add_argument('output', help='Output YAML file')
    parser.add_argument('--mrcf', help='MRCF JSON file')
    parser.add_argument('--helm', help='Helm charts directory')
    parser.add_argument('--flavor', default='standard-system',
                       choices=['small-system', 'standard-system', 'large-system'],
                       help='System size flavor')
    parser.add_argument('--method', default='rule-based',
                       choices=['rule-based', 'ML-based', 'GenAI-LLM-based', 'GenAI-SMLM-based'],
                       help='Uncommenting method (default: rule-based)')
    parser.add_argument('--log', help='Log file path')

    args = parser.parse_args()

    if args.method != 'rule-based':
        print(f"Method '{args.method}' not yet implemented. Using rule-based.")

    uncommenter = YAMLUncommenter(log_path=args.log)
    success = uncommenter.process(
        input_path=args.input,
        output_path=args.output,
        mrcf_path=args.mrcf,
        helm_path=args.helm,
        system_size=args.flavor
    )

    if success:
        print(f"Successfully processed: {args.output}")
    else:
        print("Processing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()