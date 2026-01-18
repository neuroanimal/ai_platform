"""
JSON Schema Reorder Tool for AI Platform
Minimal integration of JSON Schema reordering functionality
"""
import os
import json
import copy
from typing import Dict, Any, Optional, Union


class JSONSchemaReorder:
    """Minimal JSON Schema reordering tool integrated into AI Platform."""
    
    SCHEMA_KEYWORD_ORDER = [
        "$schema", "$id", "type", "items", "properties", 
        "patternProperties", "required", "additionalProperties"
    ]
    
    LEAF_BLACKLIST = {"properties", "patternProperties", "items", "allOf", "anyOf", "oneOf"}
    
    def reorder(self, schema: Dict[str, Any], reference: Optional[Dict[str, Any]] = None,
                sort_keywords: bool = True, merge_leaf_properties: bool = False) -> Dict[str, Any]:
        """Reorder JSON Schema based on reference."""
        return self._reorder_dict(schema, reference or {}, sort_keywords, merge_leaf_properties)
    
    def reorder_from_files(self, schema_path: str, reference_path: Optional[str] = None,
                          output_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Reorder JSON Schema from files."""
        # Load schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Load reference if provided
        reference = None
        if reference_path and os.path.exists(reference_path):
            reference = self._load_reference(reference_path)
        
        # Reorder
        result = self.reorder(schema, reference, **kwargs)
        
        # Save if output path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        return result
    
    def _load_reference(self, path: str) -> Optional[Dict[str, Any]]:
        """Load reference from JSON or YAML file."""
        try:
            _, ext = os.path.splitext(path)
            with open(path, 'r', encoding='utf-8') as f:
                if ext.lower() in ('.yml', '.yaml'):
                    try:
                        import yaml
                        return yaml.safe_load(f)
                    except ImportError:
                        raise RuntimeError("PyYAML required for YAML files")
                else:
                    return json.load(f)
        except Exception:
            return None
    
    def _reorder_dict(self, src: Dict[str, Any], ref: Dict[str, Any], 
                     sort_keywords: bool, merge_leaf: bool) -> Dict[str, Any]:
        """Reorder dictionary based on reference."""
        if not isinstance(src, dict):
            return src
        if not isinstance(ref, dict):
            ref = {}
        
        # Determine key order
        if sort_keywords:
            ordered = [k for k in self.SCHEMA_KEYWORD_ORDER if k in src]
            ordered += [k for k in src.keys() if k not in ordered]
        else:
            ordered = list(src.keys())
        
        result = {}
        
        # Process each key
        for key in ordered:
            val = src.get(key)
            
            if key == "properties" and isinstance(val, dict):
                result[key] = self._reorder_map(val, ref.get(key, {}), sort_keywords, merge_leaf)
            elif key == "patternProperties" and isinstance(val, dict):
                result[key] = self._reorder_map(val, ref.get(key, {}), sort_keywords, merge_leaf)
            elif key == "items":
                result[key] = self._reorder_items(val, ref.get(key, {}), sort_keywords, merge_leaf)
            else:
                if isinstance(val, dict) and isinstance(ref.get(key), dict):
                    result[key] = self._reorder_dict(val, ref.get(key), sort_keywords, merge_leaf)
                else:
                    result[key] = val
        
        # Merge leaf properties if needed
        if merge_leaf and self._is_leaf_schema(result):
            result = self._merge_leaf_properties(result, ref)
        
        # Move additionalProperties to end
        if "additionalProperties" in result:
            ap = result.pop("additionalProperties")
            result["additionalProperties"] = ap
        
        return result
    
    def _reorder_map(self, src_map: Dict[str, Any], ref_map: Dict[str, Any],
                    sort_keywords: bool, merge_leaf: bool) -> Dict[str, Any]:
        """Reorder map by reference order."""
        result = {}
        
        # Apply reference order first
        for k in ref_map:
            if k in src_map:
                result[k] = self._reorder_dict(src_map[k], ref_map[k], sort_keywords, merge_leaf)
        
        # Add remaining keys in original order
        for k in src_map:
            if k not in result:
                result[k] = self._reorder_dict(src_map[k], ref_map.get(k, {}), sort_keywords, merge_leaf)
        
        return result
    
    def _reorder_items(self, val: Any, ref_val: Any, sort_keywords: bool, merge_leaf: bool) -> Any:
        """Reorder items based on reference."""
        if isinstance(val, dict):
            return self._reorder_dict(val, ref_val if isinstance(ref_val, dict) else {}, sort_keywords, merge_leaf)
        elif isinstance(val, list) and isinstance(ref_val, list) and ref_val:
            return [self._reorder_dict(item, ref_val[0], sort_keywords, merge_leaf) for item in val]
        else:
            return val
    
    def _is_leaf_schema(self, obj: Dict[str, Any]) -> bool:
        """Check if schema is a leaf (no structure-defining keywords)."""
        return isinstance(obj, dict) and not any(k in obj for k in self.LEAF_BLACKLIST)
    
    def _merge_leaf_properties(self, target: Dict[str, Any], ref: Dict[str, Any]) -> Dict[str, Any]:
        """Merge missing properties from reference into leaf schema."""
        if not isinstance(target, dict) or not isinstance(ref, dict):
            return target
        
        for k, v in ref.items():
            if k not in target:
                target[k] = copy.deepcopy(v)
        
        return target