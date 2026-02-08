"""
JSON Schema Processing Engine for AI Platform
Provides engine-level interface for JSON Schema reordering functionality
"""
from typing import Dict, Any, Optional
from ai_platform.common.tool.jsonschema_reorder import JSONSchemaReorder


class JSONSchemaProcessingEngine:
    """Engine wrapper for JSON Schema processing functionality."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.reorder = JSONSchemaReorder()

    def reorder_schema(self, schema: Dict[str, Any], reference: Optional[Dict[str, Any]] = None,
                      **kwargs) -> Dict[str, Any]:
        """Reorder JSON Schema with engine interface."""
        try:
            result = self.reorder.reorder(
                schema=schema,
                reference=reference,
                sort_keywords=kwargs.get('sort_keywords', True),
                merge_leaf_properties=kwargs.get('merge_leaf_properties', False)
            )

            return {
                'success': True,
                'result': result,
                'message': 'Schema reordered successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Reordering failed: {e}'
            }

    def reorder_from_files(self, schema_path: str, reference_path: Optional[str] = None,
                          output_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Reorder JSON Schema from files with engine interface."""
        try:
            result = self.reorder.reorder_from_files(
                schema_path=schema_path,
                reference_path=reference_path,
                output_path=output_path,
                **kwargs
            )

            return {
                'success': True,
                'result': result,
                'schema_path': schema_path,
                'output_path': output_path,
                'message': 'Schema processed successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Processing failed: {e}'
            }

    def get_capabilities(self) -> Dict[str, Any]:
        """Return engine capabilities."""
        return {
            'name': 'JSON Schema Processing Engine',
            'version': '1.0.0',
            'supports': [
                'schema_reordering',
                'keyword_sorting',
                'reference_based_ordering',
                'leaf_property_merging',
                'json_yaml_references'
            ],
            'formats': ['json', 'yaml'],
            'keywords': JSONSchemaReorder.SCHEMA_KEYWORD_ORDER
        }