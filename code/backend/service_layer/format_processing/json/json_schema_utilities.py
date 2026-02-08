"""
JSON Schema Utilities - Schema processing and validation utilities
Optimal integration from additional_codes_part_1
"""
import json
from typing import Dict, Any, List, Optional, Union

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError


class JSONSchemaUtilities:
    """JSON Schema processing utilities"""

    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.stats = {
            "schemas_processed": 0,
            "properties_added": 0,
            "types_fixed": 0,
            "required_cleaned": 0
        }

    def add_additional_properties(self, schema: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """Add additionalProperties to object schemas"""
        if isinstance(schema, dict):
            schema_type = schema.get("type")
            properties = schema.get("properties")

            # Add additionalProperties for object types
            if (schema_type == "object" or properties) and "additionalProperties" not in schema:
                schema["additionalProperties"] = True
                self.stats["properties_added"] += 1
                self.tracer.debug(f"Added additionalProperties to {parent_key}")

            # Recursively process nested schemas
            for key, value in schema.items():
                if isinstance(value, dict):
                    current_key = f"{parent_key}.{key}" if parent_key else key
                    self.add_additional_properties(value, current_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            current_key = f"{parent_key}.{key}[{i}]" if parent_key else f"{key}[{i}]"
                            self.add_additional_properties(item, current_key)

        return schema

    def fix_type_inconsistencies(self, schema: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """Fix type inconsistencies in schema"""
        if isinstance(schema, dict):
            # Fix default value type mismatches
            if "default" in schema and "type" in schema:
                default_val = schema["default"]
                schema_type = schema["type"]

                if schema_type == "boolean" and isinstance(default_val, str):
                    schema["default"] = default_val.lower() == "true"
                    self.stats["types_fixed"] += 1
                elif schema_type == "integer" and isinstance(default_val, str):
                    try:
                        schema["default"] = int(default_val)
                        self.stats["types_fixed"] += 1
                    except ValueError:
                        pass
                elif schema_type == "number" and isinstance(default_val, str):
                    try:
                        schema["default"] = float(default_val)
                        self.stats["types_fixed"] += 1
                    except ValueError:
                        pass

            # Recursively process nested schemas
            for key, value in schema.items():
                if isinstance(value, dict):
                    current_key = f"{parent_key}.{key}" if parent_key else key
                    self.fix_type_inconsistencies(value, current_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            current_key = f"{parent_key}.{key}[{i}]" if parent_key else f"{key}[{i}]"
                            self.fix_type_inconsistencies(item, current_key)

        return schema

    def clean_dead_required(self, schema: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """Remove dead required properties"""
        if isinstance(schema, dict):
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            if required and properties:
                # Remove required items that don't exist in properties
                valid_required = [req for req in required if req in properties]

                if len(valid_required) != len(required):
                    if valid_required:
                        schema["required"] = valid_required
                    else:
                        del schema["required"]

                    self.stats["required_cleaned"] += 1
                    self.tracer.debug(f"Cleaned required array at {parent_key}")

            elif required and not properties:
                # Remove required array if no properties exist
                del schema["required"]
                self.stats["required_cleaned"] += 1
                self.tracer.debug(f"Removed dead required array at {parent_key}")

            # Recursively process nested schemas
            for key, value in schema.items():
                if isinstance(value, dict):
                    current_key = f"{parent_key}.{key}" if parent_key else key
                    self.clean_dead_required(value, current_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            current_key = f"{parent_key}.{key}[{i}]" if parent_key else f"{key}[{i}]"
                            self.clean_dead_required(item, current_key)

        return schema

    def extend_enum_with_default(self, schema: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """Extend enum arrays with default values if missing"""
        if isinstance(schema, dict):
            enum_values = schema.get("enum", [])
            default_value = schema.get("default")

            if enum_values and default_value is not None and default_value not in enum_values:
                schema["enum"].append(default_value)
                self.tracer.debug(f"Added default value to enum at {parent_key}")

            # Recursively process nested schemas
            for key, value in schema.items():
                if isinstance(value, dict):
                    current_key = f"{parent_key}.{key}" if parent_key else key
                    self.extend_enum_with_default(value, current_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            current_key = f"{parent_key}.{key}[{i}]" if parent_key else f"{key}[{i}]"
                            self.extend_enum_with_default(item, current_key)

        return schema

    def process_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Process schema with all utilities"""
        self.tracer.info("Processing JSON Schema with utilities")

        # Apply all processing steps
        schema = self.add_additional_properties(schema)
        schema = self.fix_type_inconsistencies(schema)
        schema = self.clean_dead_required(schema)
        schema = self.extend_enum_with_default(schema)

        self.stats["schemas_processed"] += 1
        self.tracer.info("Schema processing completed")

        return schema

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return self.stats