#!/usr/bin/env python3
"""
Example usage of AI Platform JSON Schema Processing
"""
import os
import sys
import json
import tempfile

# Add AI Platform to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from code.common.tool.jsonschema_reorder import JSONSchemaReorder
from code.common.engine.jsonschema_processing_engine import JSONSchemaProcessingEngine


def example_direct_usage():
    """Example of direct tool usage."""
    print("=== Direct Tool Usage ===")
    
    # Sample JSON Schema (unordered)
    schema = {
        "additionalProperties": False,
        "properties": {
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string", "minLength": 1},
            "age": {"type": "integer", "minimum": 0}
        },
        "required": ["name", "email"],
        "type": "object",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://example.com/person.schema.json"
    }
    
    # Reference for property ordering
    reference = {
        "properties": {
            "name": {},
            "age": {},
            "email": {}
        }
    }
    
    reorder = JSONSchemaReorder()
    result = reorder.reorder(schema, reference)
    
    print("Original schema keys:", list(schema.keys()))
    print("Reordered schema keys:", list(result.keys()))
    print("Property order:", list(result["properties"].keys()))
    print("✓ Schema reordered successfully")


def example_file_processing():
    """Example of file-based processing."""
    print("\n=== File Processing ===")
    
    schema = {
        "required": ["id"],
        "properties": {
            "status": {"type": "string", "enum": ["active", "inactive"]},
            "id": {"type": "string"},
            "metadata": {
                "type": "object",
                "properties": {
                    "updated": {"type": "string", "format": "date-time"},
                    "created": {"type": "string", "format": "date-time"}
                }
            }
        },
        "type": "object",
        "$schema": "http://json-schema.org/draft-07/schema#"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
        json.dump(schema, schema_file, indent=2)
        schema_file.flush()
        
        output_path = schema_file.name.replace('.json', '_reordered.json')
        
        reorder = JSONSchemaReorder()
        result = reorder.reorder_from_files(
            schema_path=schema_file.name,
            output_path=output_path,
            sort_keywords=True
        )
        
        print(f"✓ Processed file: {output_path}")
        
        # Show result
        with open(output_path, 'r') as f:
            reordered = json.load(f)
            print("Reordered keys:", list(reordered.keys()))
        
        # Cleanup
        os.unlink(schema_file.name)
        os.unlink(output_path)


def example_engine_usage():
    """Example of engine interface usage."""
    print("\n=== Engine Interface Usage ===")
    
    schema = {
        "patternProperties": {
            "^[a-z]+$": {"type": "string"}
        },
        "additionalProperties": False,
        "type": "object",
        "$schema": "http://json-schema.org/draft-07/schema#"
    }
    
    engine = JSONSchemaProcessingEngine()
    
    # Show capabilities
    caps = engine.get_capabilities()
    print(f"Engine: {caps['name']} v{caps['version']}")
    print(f"Supports: {', '.join(caps['supports'])}")
    
    # Process schema
    result = engine.reorder_schema(schema, sort_keywords=True)
    
    if result['success']:
        print(f"✓ {result['message']}")
        reordered = result['result']
        print("Schema keys:", list(reordered.keys()))
    else:
        print(f"✗ {result['message']}")


def main():
    """Run examples."""
    print("AI Platform JSON Schema Processing Examples")
    print("=" * 50)
    
    example_direct_usage()
    example_file_processing()
    example_engine_usage()
    
    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    main()