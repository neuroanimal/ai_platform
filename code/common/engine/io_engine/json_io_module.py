"""
JSON IO Module - Enhanced JSON processing with validation
Integrated from uncomment project with improvements
"""
import json
import os
from typing import Dict, Any, List, Optional

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError


class JSONIOModule:
    """Advanced JSON I/O with validation and quality analysis"""

    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.stats = {
            "files_read": 0,
            "files_written": 0,
            "validation_warnings": 0,
            "preprocessed_keys": 0
        }

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read JSON file with validation"""
        try:
            if not os.path.exists(file_path):
                raise FormatProcessingError(f"JSON file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Preprocessing
            processed_content = self._preprocessing(content)

            # Parse JSON
            data = json.loads(processed_content)

            # Quality analysis
            self._analyze_quality(data, file_path)

            self.stats["files_read"] += 1
            self.tracer.info(f"Successfully loaded JSON: {file_path}")
            return data

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON syntax in {file_path}: {str(e)}"
            self.tracer.error(error_msg)
            raise FormatProcessingError(error_msg)
        except Exception as e:
            error_msg = f"Failed to read JSON file {file_path}: {str(e)}"
            self.tracer.error(error_msg)
            raise FormatProcessingError(error_msg)

    def write_file(self, data: Dict[str, Any], output_path: str, indent: int = 4) -> bool:
        """Write JSON file with formatting"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False, sort_keys=True)

            self.stats["files_written"] += 1
            self.tracer.info(f"Successfully wrote JSON: {output_path}")
            return True

        except Exception as e:
            error_msg = f"Failed to write JSON file {output_path}: {str(e)}"
            self.tracer.error(error_msg)
            raise FormatProcessingError(error_msg)

    def read_parameters(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract parameters list from flat JSON"""
        data = self.read_file(file_path)

        if isinstance(data, dict) and "parameters" in data:
            parameters = data["parameters"]
            self.tracer.info(f"Loaded {len(parameters)} parameter definitions from JSON")
            return parameters
        elif isinstance(data, list):
            self.tracer.info(f"Loaded {len(data)} parameters from JSON array")
            return data
        else:
            self.tracer.warning(f"No parameters found in JSON file: {file_path}")
            return []

    def read_flat_json(self, file_path: str) -> Dict[str, Any]:
        """Read flat JSON structure (key-value pairs)"""
        data = self.read_file(file_path)

        if not isinstance(data, dict):
            raise FormatProcessingError(f"Expected flat JSON object, got {type(data).__name__}")

        # Flatten nested structures if needed
        flattened = self._flatten_dict(data)
        return flattened

    def _preprocessing(self, content: str) -> str:
        """Preprocess JSON content"""
        # Remove comments if present (non-standard JSON)
        import re
        content = re.sub(r'//.*?\n', '\n', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        return content.strip()

    def _analyze_quality(self, data: Dict[str, Any], file_name: str):
        """Analyze JSON quality and detect issues"""
        if not isinstance(data, (dict, list)):
            self.tracer.warning(f"File {file_name} contains neither object nor array")
            return

        if isinstance(data, dict):
            for key, value in data.items():
                # Check for null values
                if value is None:
                    self.tracer.debug(f"Null value for key: {key}")
                    self.stats["validation_warnings"] += 1

                # Check for string booleans
                if isinstance(value, str) and value.lower() in ['true', 'false']:
                    self.tracer.debug(f"Key {key} contains boolean as string")
                    self.stats["validation_warnings"] += 1

                # Check for empty strings
                if isinstance(value, str) and not value.strip():
                    self.tracer.debug(f"Empty string value for key: {key}")
                    self.stats["validation_warnings"] += 1

    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        items.extend(self._flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
                    else:
                        items.append((f"{new_key}[{i}]", item))
            else:
                items.append((new_key, value))

        return dict(items)

    def validate_json(self, file_path: str) -> bool:
        """Validate JSON file syntax"""
        try:
            self.read_file(file_path)
            return True
        except FormatProcessingError:
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return self.stats