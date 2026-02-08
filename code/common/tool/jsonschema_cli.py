#!/usr/bin/env python3
"""
AI Platform JSON Schema Reorder CLI
"""
import sys
import os
import argparse
import json

# Add AI Platform to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from ai_platform.common.tool.jsonschema_reorder import JSONSchemaReorder


def main():
    parser = argparse.ArgumentParser(description='AI Platform JSON Schema Reorder')
    parser.add_argument('schema', help='Input JSON Schema file')
    parser.add_argument('output', help='Output JSON Schema file')
    parser.add_argument('--reference', help='Reference JSON/YAML file for ordering')
    parser.add_argument('--no-sort', action='store_true', help='Keep original keyword order')
    parser.add_argument('--merge-leaf', action='store_true', help='Merge leaf properties from reference')
    parser.add_argument('--pretty', action='store_true', help='Pretty print output')

    args = parser.parse_args()

    reorder = JSONSchemaReorder()

    try:
        result = reorder.reorder_from_files(
            schema_path=args.schema,
            reference_path=args.reference,
            output_path=args.output,
            sort_keywords=not args.no_sort,
            merge_leaf_properties=args.merge_leaf
        )

        if args.pretty:
            print("Reordered schema:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

        print(f"Successfully reordered schema: {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()