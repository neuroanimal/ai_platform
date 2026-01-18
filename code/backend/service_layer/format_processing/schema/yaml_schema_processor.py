"""
YAML Schema Processing Module
Handles YAML-based schemas (like JSON Schema but using YAML format)
"""
import yaml
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import jsonschema
from pathlib import Path

class SchemaFormat(Enum):
    JSON_SCHEMA = "json_schema"
    YAML_SCHEMA = "yaml_schema"
    OPENAPI = "openapi"
    ASYNCAPI = "asyncapi"

@dataclass
class SchemaValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
    schema_format: SchemaFormat
    data_format: str

@dataclass
class SchemaConversionResult:
    success: bool
    converted_schema: Dict[str, Any]
    source_format: SchemaFormat
    target_format: SchemaFormat
    error: Optional[str] = None

class YAMLSchemaProcessor:
    """Processor for YAML-based schemas and validation"""
    
    def __init__(self):
        self.meta_schemas = {
            SchemaFormat.JSON_SCHEMA: "http://json-schema.org/draft-07/schema#",
            SchemaFormat.YAML_SCHEMA: "http://yaml-schema.org/draft-01/schema#",
            SchemaFormat.OPENAPI: "https://spec.openapis.org/oas/v3.0.3/schema/",
            SchemaFormat.ASYNCAPI: "https://www.asyncapi.com/definitions/2.4.0/asyncapi.json"
        }
        
        self.schema_indicators = {
            SchemaFormat.JSON_SCHEMA: ['$schema', 'type', 'properties'],
            SchemaFormat.YAML_SCHEMA: ['$schema', 'type', 'properties', 'yaml-schema'],
            SchemaFormat.OPENAPI: ['openapi', 'info', 'paths'],
            SchemaFormat.ASYNCAPI: ['asyncapi', 'info', 'channels']
        }
    
    def load_schema(self, file_path: str, schema_format: Optional[SchemaFormat] = None) -> Dict[str, Any]:
        """Load schema from file"""
        path = Path(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ['.yml', '.yaml']:
                schema = yaml.safe_load(f)
            else:
                schema = json.load(f)
        
        if not schema_format:
            schema_format = self.detect_schema_format(schema)
        
        # Add format metadata
        schema['_schema_format'] = schema_format.value
        
        return schema
    
    def detect_schema_format(self, schema: Dict[str, Any]) -> SchemaFormat:
        """Auto-detect schema format"""
        
        for format_type, indicators in self.schema_indicators.items():
            if any(indicator in schema for indicator in indicators):
                return format_type
        
        # Default to JSON Schema if uncertain
        return SchemaFormat.JSON_SCHEMA
    
    def validate_data_against_schema(self, data: Any, schema: Dict[str, Any], 
                                   data_format: str = 'json') -> SchemaValidationResult:
        """Validate data against schema"""
        
        schema_format = SchemaFormat(schema.get('_schema_format', 'json_schema'))
        errors = []
        warnings = []
        
        try:
            if schema_format in [SchemaFormat.JSON_SCHEMA, SchemaFormat.YAML_SCHEMA]:
                # Use jsonschema library for validation
                validator = jsonschema.Draft7Validator(schema)
                validation_errors = list(validator.iter_errors(data))
                
                for error in validation_errors:
                    error_path = " -> ".join(str(p) for p in error.absolute_path)
                    error_msg = f"Path '{error_path}': {error.message}"
                    errors.append(error_msg)
            
            elif schema_format == SchemaFormat.OPENAPI:
                # Validate against OpenAPI schema
                validation_result = self._validate_openapi_data(data, schema)
                errors.extend(validation_result['errors'])
                warnings.extend(validation_result['warnings'])
            
            elif schema_format == SchemaFormat.ASYNCAPI:
                # Validate against AsyncAPI schema
                validation_result = self._validate_asyncapi_data(data, schema)
                errors.extend(validation_result['errors'])
                warnings.extend(validation_result['warnings'])
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return SchemaValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            schema_format=schema_format,
            data_format=data_format
        )
    
    def convert_schema_format(self, schema: Dict[str, Any], 
                            target_format: SchemaFormat) -> SchemaConversionResult:
        """Convert schema between formats"""
        
        source_format = SchemaFormat(schema.get('_schema_format', 'json_schema'))
        
        try:
            if source_format == target_format:
                return SchemaConversionResult(True, schema, source_format, target_format)
            
            converted_schema = self._perform_schema_conversion(schema, source_format, target_format)
            
            return SchemaConversionResult(
                success=True,
                converted_schema=converted_schema,
                source_format=source_format,
                target_format=target_format
            )
            
        except Exception as e:
            return SchemaConversionResult(
                success=False,
                converted_schema={},
                source_format=source_format,
                target_format=target_format,
                error=str(e)
            )
    
    def generate_schema_from_data(self, data: Any, target_format: SchemaFormat = SchemaFormat.YAML_SCHEMA) -> Dict[str, Any]:
        """Generate schema from sample data"""
        
        schema = {
            "$schema": self.meta_schemas[target_format],
            "_schema_format": target_format.value
        }
        
        schema.update(self._infer_schema_from_value(data))
        
        return schema
    
    def validate_schema_syntax(self, schema: Dict[str, Any]) -> SchemaValidationResult:
        """Validate schema syntax against meta-schema"""
        
        schema_format = SchemaFormat(schema.get('_schema_format', 'json_schema'))
        errors = []
        warnings = []
        
        try:
            if schema_format in [SchemaFormat.JSON_SCHEMA, SchemaFormat.YAML_SCHEMA]:
                # Validate against JSON Schema meta-schema
                meta_schema_url = self.meta_schemas[schema_format]
                jsonschema.validate(schema, {"$ref": meta_schema_url})
            
            # Additional format-specific validations
            format_errors = self._validate_format_specific_syntax(schema, schema_format)
            errors.extend(format_errors)
            
        except jsonschema.ValidationError as e:
            errors.append(f"Schema syntax error: {e.message}")
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")
        
        return SchemaValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            schema_format=schema_format,
            data_format='schema'
        )
    
    def merge_schemas(self, schemas: List[Dict[str, Any]], 
                     merge_strategy: str = 'union') -> Dict[str, Any]:
        """Merge multiple schemas"""
        
        if not schemas:
            return {}
        
        if len(schemas) == 1:
            return schemas[0]
        
        # Determine common format
        formats = [SchemaFormat(s.get('_schema_format', 'json_schema')) for s in schemas]
        target_format = max(set(formats), key=formats.count)
        
        # Convert all schemas to common format
        converted_schemas = []
        for schema in schemas:
            conversion_result = self.convert_schema_format(schema, target_format)
            if conversion_result.success:
                converted_schemas.append(conversion_result.converted_schema)
        
        # Merge schemas based on strategy
        if merge_strategy == 'union':
            return self._merge_schemas_union(converted_schemas, target_format)
        elif merge_strategy == 'intersection':
            return self._merge_schemas_intersection(converted_schemas, target_format)
        else:
            return self._merge_schemas_override(converted_schemas, target_format)
    
    def _perform_schema_conversion(self, schema: Dict[str, Any], 
                                 source_format: SchemaFormat, 
                                 target_format: SchemaFormat) -> Dict[str, Any]:
        """Perform actual schema conversion"""
        
        converted = schema.copy()
        
        # Update schema reference
        if '$schema' in converted:
            converted['$schema'] = self.meta_schemas[target_format]
        
        # Format-specific conversions
        if source_format == SchemaFormat.JSON_SCHEMA and target_format == SchemaFormat.YAML_SCHEMA:
            # Add YAML-specific extensions
            converted['yaml-schema'] = True
            if 'examples' in converted:
                converted['yaml-examples'] = converted['examples']
        
        elif source_format == SchemaFormat.YAML_SCHEMA and target_format == SchemaFormat.JSON_SCHEMA:
            # Remove YAML-specific extensions
            converted.pop('yaml-schema', None)
            converted.pop('yaml-examples', None)
        
        elif target_format == SchemaFormat.OPENAPI:
            # Convert to OpenAPI format
            converted = self._convert_to_openapi(converted)
        
        elif target_format == SchemaFormat.ASYNCAPI:
            # Convert to AsyncAPI format
            converted = self._convert_to_asyncapi(converted)
        
        converted['_schema_format'] = target_format.value
        
        return converted
    
    def _infer_schema_from_value(self, value: Any) -> Dict[str, Any]:
        """Infer schema structure from a value"""
        
        if value is None:
            return {"type": "null"}
        
        elif isinstance(value, bool):
            return {"type": "boolean"}
        
        elif isinstance(value, int):
            return {"type": "integer"}
        
        elif isinstance(value, float):
            return {"type": "number"}
        
        elif isinstance(value, str):
            return {"type": "string"}
        
        elif isinstance(value, list):
            if not value:
                return {"type": "array", "items": {}}
            
            # Infer items schema from first element
            items_schema = self._infer_schema_from_value(value[0])
            return {"type": "array", "items": items_schema}
        
        elif isinstance(value, dict):
            properties = {}
            required = []
            
            for key, val in value.items():
                properties[key] = self._infer_schema_from_value(val)
                if val is not None:
                    required.append(key)
            
            schema = {"type": "object", "properties": properties}
            if required:
                schema["required"] = required
            
            return schema
        
        else:
            return {"type": "string", "description": f"Inferred from {type(value).__name__}"}
    
    def _validate_openapi_data(self, data: Any, schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate data against OpenAPI schema"""
        errors = []
        warnings = []
        
        # Basic OpenAPI validation
        if 'openapi' not in schema:
            errors.append("Missing 'openapi' field in schema")
        
        if 'info' not in schema:
            errors.append("Missing 'info' field in schema")
        
        # Validate paths if present
        if 'paths' in schema and isinstance(data, dict) and 'paths' in data:
            for path, path_data in data['paths'].items():
                if path not in schema['paths']:
                    warnings.append(f"Path '{path}' not defined in schema")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_asyncapi_data(self, data: Any, schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate data against AsyncAPI schema"""
        errors = []
        warnings = []
        
        # Basic AsyncAPI validation
        if 'asyncapi' not in schema:
            errors.append("Missing 'asyncapi' field in schema")
        
        if 'info' not in schema:
            errors.append("Missing 'info' field in schema")
        
        # Validate channels if present
        if 'channels' in schema and isinstance(data, dict) and 'channels' in data:
            for channel, channel_data in data['channels'].items():
                if channel not in schema['channels']:
                    warnings.append(f"Channel '{channel}' not defined in schema")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_format_specific_syntax(self, schema: Dict[str, Any], 
                                       schema_format: SchemaFormat) -> List[str]:
        """Validate format-specific syntax"""
        errors = []
        
        if schema_format == SchemaFormat.YAML_SCHEMA:
            # YAML Schema specific validations
            if 'yaml-schema' in schema and not isinstance(schema['yaml-schema'], bool):
                errors.append("'yaml-schema' field must be boolean")
        
        elif schema_format == SchemaFormat.OPENAPI:
            # OpenAPI specific validations
            if 'openapi' in schema:
                version = schema['openapi']
                if not isinstance(version, str) or not version.startswith('3.'):
                    errors.append("OpenAPI version must be 3.x.x")
        
        elif schema_format == SchemaFormat.ASYNCAPI:
            # AsyncAPI specific validations
            if 'asyncapi' in schema:
                version = schema['asyncapi']
                if not isinstance(version, str) or not version.startswith('2.'):
                    errors.append("AsyncAPI version must be 2.x.x")
        
        return errors
    
    def _convert_to_openapi(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert schema to OpenAPI format"""
        openapi_schema = {
            "openapi": "3.0.3",
            "info": {
                "title": schema.get('title', 'Generated API'),
                "version": "1.0.0",
                "description": schema.get('description', 'Generated from schema')
            },
            "paths": {},
            "components": {
                "schemas": {
                    "MainSchema": schema
                }
            }
        }
        
        return openapi_schema
    
    def _convert_to_asyncapi(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert schema to AsyncAPI format"""
        asyncapi_schema = {
            "asyncapi": "2.4.0",
            "info": {
                "title": schema.get('title', 'Generated Async API'),
                "version": "1.0.0",
                "description": schema.get('description', 'Generated from schema')
            },
            "channels": {},
            "components": {
                "schemas": {
                    "MainSchema": schema
                }
            }
        }
        
        return asyncapi_schema
    
    def _merge_schemas_union(self, schemas: List[Dict[str, Any]], 
                           target_format: SchemaFormat) -> Dict[str, Any]:
        """Merge schemas using union strategy"""
        merged = {
            "$schema": self.meta_schemas[target_format],
            "_schema_format": target_format.value,
            "anyOf": schemas
        }
        
        return merged
    
    def _merge_schemas_intersection(self, schemas: List[Dict[str, Any]], 
                                  target_format: SchemaFormat) -> Dict[str, Any]:
        """Merge schemas using intersection strategy"""
        merged = {
            "$schema": self.meta_schemas[target_format],
            "_schema_format": target_format.value,
            "allOf": schemas
        }
        
        return merged
    
    def _merge_schemas_override(self, schemas: List[Dict[str, Any]], 
                              target_format: SchemaFormat) -> Dict[str, Any]:
        """Merge schemas using override strategy (last wins)"""
        merged = {
            "$schema": self.meta_schemas[target_format],
            "_schema_format": target_format.value
        }
        
        for schema in schemas:
            merged.update(schema)
        
        return merged