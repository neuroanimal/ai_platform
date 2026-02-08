"""
JSON Schema Processing Service - Full Integration
Complete merge of jsonschema_reorder functionality into AI Platform
"""
import os
import json
import copy
from typing import Dict, Any, Optional, List, Union
from pathlib import Path


class JSONSchemaProcessingService:
    """Complete JSON Schema processing service with all jsonschema_reorder functionality."""

    # Full schema keyword order from original
    SCHEMA_KEYWORD_ORDER = [
        "$schema",
        "$id",
        "$ref",
        "$defs",
        "$vocabulary",
        "$comment",
        "title",
        "description",
        "default",
        "examples",
        "readOnly",
        "writeOnly",
        "deprecated",
        "type",
        "enum",
        "const",
        "multipleOf",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
        "maxLength",
        "minLength",
        "pattern",
        "maxItems",
        "minItems",
        "uniqueItems",
        "maxContains",
        "minContains",
        "maxProperties",
        "minProperties",
        "required",
        "dependentRequired",
        "format",
        "contentMediaType",
        "contentEncoding",
        "contentSchema",
        "if",
        "then",
        "else",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "items",
        "prefixItems",
        "contains",
        "additionalItems",
        "unevaluatedItems",
        "properties",
        "patternProperties",
        "additionalProperties",
        "unevaluatedProperties",
        "propertyNames",
        "dependentSchemas"
    ]

    # Keywords that define structure (not leaf schemas)
    LEAF_BLACKLIST = {
        "properties", "patternProperties", "items", "prefixItems", "contains",
        "additionalItems", "unevaluatedItems", "additionalProperties",
        "unevaluatedProperties", "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
        "dependentSchemas", "$defs"
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = self._init_config(config)

    def _init_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Initialize configuration with defaults."""
        default_config = {
            'sort_keywords': True,
            'merge_leaf_properties': False,
            'preserve_order': False,
            'indent': 2,
            'ensure_ascii': False,
            'encoding': 'utf-8'
        }

        if config:
            default_config.update(config)
        return default_config

    def reorder_schema(self, schema: Dict[str, Any], reference: Optional[Dict[str, Any]] = None,
                      sort_keywords: Optional[bool] = None,
                      merge_leaf_properties: Optional[bool] = None) -> Dict[str, Any]:
        """
        Reorder JSON Schema based on reference schema.

        Args:
            schema: Source JSON Schema to reorder
            reference: Reference schema for ordering (optional)
            sort_keywords: Whether to sort keywords by standard order
            merge_leaf_properties: Whether to merge missing properties from reference

        Returns:
            Reordered JSON Schema
        """
        if sort_keywords is None:
            sort_keywords = self.config['sort_keywords']
        if merge_leaf_properties is None:
            merge_leaf_properties = self.config['merge_leaf_properties']

        return self._reorder_dict_keep_keywords(
            schema,
            reference or {},
            sort_keywords=sort_keywords,
            merge_leaf_properties_flag=merge_leaf_properties
        )

    def reorder_from_files(self, schema_path: str, reference_path: Optional[str] = None,
                          output_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Reorder JSON Schema from files.

        Args:
            schema_path: Path to source schema file
            reference_path: Path to reference file (JSON/YAML)
            output_path: Path to output file (optional)
            **kwargs: Additional options

        Returns:
            Processing result with reordered schema
        """
        try:
            # Load source schema
            with open(schema_path, 'r', encoding=self.config['encoding']) as f:
                schema = json.load(f)

            # Load reference if provided
            reference = None
            if reference_path and os.path.exists(reference_path):
                reference = self._load_reference_maybe(reference_path)

            # Reorder schema
            result = self.reorder_schema(schema, reference, **kwargs)

            # Save to output file if specified
            if output_path:
                with open(output_path, 'w', encoding=self.config['encoding']) as f:
                    json.dump(result, f, indent=self.config['indent'],
                             ensure_ascii=self.config['ensure_ascii'])

            return {
                'success': True,
                'result': result,
                'schema_path': schema_path,
                'reference_path': reference_path,
                'output_path': output_path,
                'message': 'Schema reordered successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'schema_path': schema_path,
                'message': f'Reordering failed: {e}'
            }

    def batch_reorder(self, schema_paths: List[str], reference_path: Optional[str] = None,
                     output_dir: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Batch reorder multiple JSON Schema files.

        Args:
            schema_paths: List of schema file paths
            reference_path: Path to reference file
            output_dir: Output directory for reordered files
            **kwargs: Additional options

        Returns:
            Batch processing results
        """
        results = []
        successful = 0
        failed = 0

        for schema_path in schema_paths:
            try:
                output_path = None
                if output_dir:
                    filename = os.path.basename(schema_path)
                    name, ext = os.path.splitext(filename)
                    output_path = os.path.join(output_dir, f"{name}_reordered{ext}")

                result = self.reorder_from_files(
                    schema_path=schema_path,
                    reference_path=reference_path,
                    output_path=output_path,
                    **kwargs
                )

                results.append(result)
                if result['success']:
                    successful += 1
                else:
                    failed += 1

            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                    'schema_path': schema_path,
                    'message': f'Processing failed: {e}'
                })
                failed += 1

        return {
            'success': failed == 0,
            'results': results,
            'total': len(schema_paths),
            'successful': successful,
            'failed': failed,
            'message': f'Processed {successful}/{len(schema_paths)} schemas successfully'
        }

    def validate_schema_structure(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate JSON Schema structure and provide recommendations.

        Args:
            schema: JSON Schema to validate

        Returns:
            Validation results with recommendations
        """
        issues = []
        recommendations = []

        # Check for required fields
        if '$schema' not in schema:
            issues.append("Missing '$schema' field")
            recommendations.append("Add '$schema' field to specify JSON Schema version")

        if 'type' not in schema and '$ref' not in schema:
            issues.append("Missing 'type' field")
            recommendations.append("Add 'type' field to specify data type")

        # Check keyword order
        if self.config['sort_keywords']:
            current_order = list(schema.keys())
            expected_order = [k for k in self.SCHEMA_KEYWORD_ORDER if k in schema]
            expected_order += [k for k in current_order if k not in expected_order]

            if current_order != expected_order:
                issues.append("Keywords not in recommended order")
                recommendations.append("Reorder keywords according to JSON Schema best practices")

        # Check for additionalProperties placement
        if 'additionalProperties' in schema:
            keys = list(schema.keys())
            if keys[-1] != 'additionalProperties':
                issues.append("'additionalProperties' should be last")
                recommendations.append("Move 'additionalProperties' to end of schema")

        # Validate nested schemas
        nested_issues = self._validate_nested_schemas(schema, "")
        issues.extend(nested_issues)

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'recommendations': recommendations,
            'schema_type': schema.get('type', 'unknown'),
            'has_properties': 'properties' in schema,
            'has_items': 'items' in schema
        }

    def _validate_nested_schemas(self, schema: Any, path: str) -> List[str]:
        """Validate nested schemas recursively."""
        issues = []

        if not isinstance(schema, dict):
            return issues

        # Check properties
        if 'properties' in schema and isinstance(schema['properties'], dict):
            for prop_name, prop_schema in schema['properties'].items():
                prop_path = f"{path}.properties.{prop_name}" if path else f"properties.{prop_name}"
                issues.extend(self._validate_nested_schemas(prop_schema, prop_path))

        # Check items
        if 'items' in schema:
            items_path = f"{path}.items" if path else "items"
            if isinstance(schema['items'], dict):
                issues.extend(self._validate_nested_schemas(schema['items'], items_path))
            elif isinstance(schema['items'], list):
                for i, item_schema in enumerate(schema['items']):
                    issues.extend(self._validate_nested_schemas(item_schema, f"{items_path}[{i}]"))

        # Check other schema-containing keywords
        for keyword in ['allOf', 'anyOf', 'oneOf']:
            if keyword in schema and isinstance(schema[keyword], list):
                for i, sub_schema in enumerate(schema[keyword]):
                    sub_path = f"{path}.{keyword}[{i}]" if path else f"{keyword}[{i}]"
                    issues.extend(self._validate_nested_schemas(sub_schema, sub_path))

        return issues

    def _reorder_dict_keep_keywords(self, src: Dict[str, Any], ref: Dict[str, Any], *,
                                   sort_keywords: bool = True,
                                   merge_leaf_properties_flag: bool = False) -> Dict[str, Any]:
        """
        Reorder dictionary keeping keywords - full original implementation.

        This is the core reordering function from the original jsonschema_reorder.
        """
        if not isinstance(src, dict):
            return src
        if not isinstance(ref, dict):
            ref = {}

        # Determine initial key order
        if sort_keywords:
            # First schema keywords in standard order
            ordered = [k for k in self.SCHEMA_KEYWORD_ORDER if k in src]
            # Then remaining keys in original order
            ordered += [k for k in src.keys() if k not in ordered]
        else:
            # Keep original order
            ordered = list(src.keys())

        out = {}

        # Process each key in the selected order
        for key in ordered:
            val = src.get(key)

            if key == "properties" and isinstance(val, dict):
                out[key] = self._reorder_map_by_reference(
                    val, ref.get(key, {}), sort_keywords, merge_leaf_properties_flag
                )

            elif key == "patternProperties" and isinstance(val, dict):
                out[key] = self._reorder_map_by_reference(
                    val, ref.get(key, {}), sort_keywords, merge_leaf_properties_flag
                )

            elif key == "items":
                if isinstance(val, dict):
                    out[key] = self._reorder_dict_keep_keywords(
                        val,
                        ref.get(key, {}),
                        sort_keywords=sort_keywords,
                        merge_leaf_properties_flag=merge_leaf_properties_flag
                    )
                elif isinstance(val, list) and isinstance(ref.get(key), list) and ref.get(key):
                    out[key] = [
                        self._reorder_dict_keep_keywords(
                            item,
                            ref.get(key)[0],
                            sort_keywords=sort_keywords,
                            merge_leaf_properties_flag=merge_leaf_properties_flag
                        )
                        for item in val
                    ]
                else:
                    out[key] = val

            elif key in ["allOf", "anyOf", "oneOf"] and isinstance(val, list):
                ref_list = ref.get(key, [])
                out[key] = []
                for i, item in enumerate(val):
                    ref_item = ref_list[i] if i < len(ref_list) else {}
                    if isinstance(item, dict):
                        out[key].append(self._reorder_dict_keep_keywords(
                            item, ref_item,
                            sort_keywords=sort_keywords,
                            merge_leaf_properties_flag=merge_leaf_properties_flag
                        ))
                    else:
                        out[key].append(item)

            elif key == "not" and isinstance(val, dict):
                out[key] = self._reorder_dict_keep_keywords(
                    val,
                    ref.get(key, {}),
                    sort_keywords=sort_keywords,
                    merge_leaf_properties_flag=merge_leaf_properties_flag
                )

            elif key in ["if", "then", "else"] and isinstance(val, dict):
                out[key] = self._reorder_dict_keep_keywords(
                    val,
                    ref.get(key, {}),
                    sort_keywords=sort_keywords,
                    merge_leaf_properties_flag=merge_leaf_properties_flag
                )

            elif key == "$defs" and isinstance(val, dict):
                out[key] = self._reorder_map_by_reference(
                    val, ref.get(key, {}), sort_keywords, merge_leaf_properties_flag
                )

            elif key == "dependentSchemas" and isinstance(val, dict):
                out[key] = self._reorder_map_by_reference(
                    val, ref.get(key, {}), sort_keywords, merge_leaf_properties_flag
                )

            else:
                if isinstance(val, dict) and isinstance(ref.get(key), dict):
                    out[key] = self._reorder_dict_keep_keywords(
                        val,
                        ref.get(key),
                        sort_keywords=sort_keywords,
                        merge_leaf_properties_flag=merge_leaf_properties_flag
                    )
                else:
                    out[key] = val

        # LEAF MERGE — AFTER nested reorder
        if merge_leaf_properties_flag and self._is_leaf_schema(out):
            out = self._merge_leaf_properties(out, ref)

        # MOVE additionalProperties TO END
        if "additionalProperties" in out:
            ap = out.pop("additionalProperties")
            out["additionalProperties"] = ap

        # Also move other "additional" keywords to end
        for end_keyword in ["unevaluatedProperties", "unevaluatedItems"]:
            if end_keyword in out:
                val = out.pop(end_keyword)
                out[end_keyword] = val

        return out

    def _reorder_map_by_reference(self, src_map: Dict[str, Any], ref_map: Dict[str, Any],
                                 sort_keywords: bool, merge_leaf_properties_flag: bool) -> Dict[str, Any]:
        """Reorder map by reference order - full original implementation."""
        result = {}

        # Apply reference order first
        for k in ref_map:
            if k in src_map:
                result[k] = self._reorder_dict_keep_keywords(
                    src_map[k],
                    ref_map[k],
                    sort_keywords=sort_keywords,
                    merge_leaf_properties_flag=merge_leaf_properties_flag
                )

        # Then remaining keys in original order
        for k in src_map:
            if k not in result:
                result[k] = self._reorder_dict_keep_keywords(
                    src_map[k],
                    ref_map.get(k, {}),
                    sort_keywords=sort_keywords,
                    merge_leaf_properties_flag=merge_leaf_properties_flag
                )

        return result

    def _is_leaf_schema(self, obj: Dict[str, Any]) -> bool:
        """Schema is leaf when it does NOT contain any of the structure-defining keywords."""
        if not isinstance(obj, dict):
            return False
        return not any(k in obj for k in self.LEAF_BLACKLIST)

    def _merge_leaf_properties(self, target: Dict[str, Any], ref: Dict[str, Any]) -> Dict[str, Any]:
        """Add missing properties from reference into leaf schema."""
        if not isinstance(target, dict) or not isinstance(ref, dict):
            return target

        for k, v in ref.items():
            if k not in target:
                target[k] = copy.deepcopy(v)

        return target

    def _load_reference_maybe(self, path: str) -> Optional[Dict[str, Any]]:
        """Load reference from JSON or YAML file - full original implementation."""
        if not os.path.exists(path):
            return None

        _, ext = os.path.splitext(path)

        try:
            with open(path, "r", encoding=self.config['encoding']) as f:
                if ext.lower() in (".yml", ".yaml"):
                    try:
                        import yaml
                        return yaml.safe_load(f)
                    except ImportError:
                        raise RuntimeError("PyYAML required for YAML reference files")
                else:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load reference file {path}: {e}")
            return None

    def get_schema_info(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive information about a JSON Schema."""
        info = {
            'schema_version': schema.get('$schema', 'unknown'),
            'schema_id': schema.get('$id', None),
            'title': schema.get('title', None),
            'description': schema.get('description', None),
            'type': schema.get('type', 'unknown'),
            'keywords': list(schema.keys()),
            'keyword_count': len(schema),
            'has_properties': 'properties' in schema,
            'has_items': 'items' in schema,
            'has_additional_properties': 'additionalProperties' in schema,
            'has_required': 'required' in schema,
            'is_leaf_schema': self._is_leaf_schema(schema),
            'complexity': self._calculate_schema_complexity(schema)
        }

        if 'properties' in schema:
            info['property_count'] = len(schema['properties'])
            info['property_names'] = list(schema['properties'].keys())

        if 'required' in schema:
            info['required_properties'] = schema['required']
            info['required_count'] = len(schema['required'])

        return info

    def _calculate_schema_complexity(self, schema: Any, depth: int = 0) -> int:
        """Calculate schema complexity score."""
        if not isinstance(schema, dict) or depth > 10:  # Prevent infinite recursion
            return 0

        complexity = 1  # Base complexity

        # Add complexity for each keyword
        complexity += len(schema)

        # Add complexity for nested schemas
        if 'properties' in schema and isinstance(schema['properties'], dict):
            for prop_schema in schema['properties'].values():
                complexity += self._calculate_schema_complexity(prop_schema, depth + 1)

        if 'items' in schema:
            if isinstance(schema['items'], dict):
                complexity += self._calculate_schema_complexity(schema['items'], depth + 1)
            elif isinstance(schema['items'], list):
                for item_schema in schema['items']:
                    complexity += self._calculate_schema_complexity(item_schema, depth + 1)

        # Add complexity for logical operators
        for keyword in ['allOf', 'anyOf', 'oneOf']:
            if keyword in schema and isinstance(schema[keyword], list):
                for sub_schema in schema[keyword]:
                    complexity += self._calculate_schema_complexity(sub_schema, depth + 1)

        return complexity