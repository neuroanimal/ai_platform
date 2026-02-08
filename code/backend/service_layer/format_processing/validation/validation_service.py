"""
Validation Service - Comprehensive validation for multiple formats
Optimal integration from additional_codes_part_2
"""
import os
import json
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError
from common.engine.io_engine.json_io_module import JSONIOModule
from common.engine.io_engine.yaml_io_module import YAMLIOModule


class ValidationService:
    """Comprehensive validation service for multiple formats"""

    def __init__(self, product: str = "AI_Platform", version: str = "1.0"):
        self.product = product
        self.version = version
        self.tracer = TraceHandler(product, version, "ValidationService")

        # Initialize IO modules
        self.json_io = JSONIOModule(self.tracer)
        self.yaml_io = YAMLIOModule(self.tracer)

        self.stats = {
            "validations_performed": 0,
            "json_validations": 0,
            "yaml_validations": 0,
            "schema_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0
        }

    def validate_json_file(self, json_file: str) -> Tuple[bool, Optional[str]]:
        """Validate JSON file syntax"""
        try:
            self.json_io.read_file(json_file)
            self.stats["json_validations"] += 1
            self.stats["successful_validations"] += 1
            self.stats["validations_performed"] += 1
            return True, None

        except Exception as e:
            error_msg = f"JSON validation failed: {str(e)}"
            self.tracer.error(error_msg)
            self.stats["json_validations"] += 1
            self.stats["failed_validations"] += 1
            self.stats["validations_performed"] += 1
            return False, error_msg

    def validate_yaml_file(self, yaml_file: str) -> Tuple[bool, Optional[str]]:
        """Validate YAML file syntax"""
        try:
            self.yaml_io.read_file(yaml_file)
            self.stats["yaml_validations"] += 1
            self.stats["successful_validations"] += 1
            self.stats["validations_performed"] += 1
            return True, None

        except Exception as e:
            error_msg = f"YAML validation failed: {str(e)}"
            self.tracer.error(error_msg)
            self.stats["yaml_validations"] += 1
            self.stats["failed_validations"] += 1
            self.stats["validations_performed"] += 1
            return False, error_msg

    def validate_json_schema(self, schema_file: str, meta_schema_file: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Validate JSON Schema against meta-schema"""
        try:
            import jsonschema

            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            if meta_schema_file and os.path.exists(meta_schema_file):
                with open(meta_schema_file, 'r', encoding='utf-8') as f:
                    meta_schema = json.load(f)
                jsonschema.validate(schema, meta_schema)
            else:
                jsonschema.Draft7Validator.check_schema(schema)

            self.stats["schema_validations"] += 1
            self.stats["successful_validations"] += 1
            self.stats["validations_performed"] += 1
            return True, None

        except Exception as e:
            error_msg = f"Schema validation failed: {str(e)}"
            self.tracer.error(error_msg)
            self.stats["schema_validations"] += 1
            self.stats["failed_validations"] += 1
            self.stats["validations_performed"] += 1
            return False, error_msg

    def validate_json_against_schema(self, json_file: str, schema_file: str) -> Tuple[bool, Optional[str]]:
        """Validate JSON data against JSON Schema"""
        try:
            import jsonschema

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            jsonschema.validate(data, schema)

            self.stats["validations_performed"] += 1
            self.stats["successful_validations"] += 1
            return True, None

        except Exception as e:
            error_msg = f"Data validation failed: {str(e)}"
            self.tracer.error(error_msg)
            self.stats["validations_performed"] += 1
            self.stats["failed_validations"] += 1
            return False, error_msg

    def validate_directory(self, directory: str, file_pattern: str = "*.json") -> Dict[str, Tuple[bool, Optional[str]]]:
        """Validate all files in directory matching pattern"""
        results = {}

        try:
            files = list(Path(directory).glob(file_pattern))

            for file_path in files:
                filename = file_path.name

                if file_pattern.endswith('.json'):
                    if 'schema.json' in filename:
                        valid, error = self.validate_json_schema(str(file_path))
                    else:
                        valid, error = self.validate_json_file(str(file_path))
                elif file_pattern.endswith(('.yaml', '.yml')):
                    valid, error = self.validate_yaml_file(str(file_path))
                else:
                    valid, error = False, f"Unsupported file type: {filename}"

                results[filename] = (valid, error)

            self.tracer.info(f"Directory validation completed: {len(results)} files processed")
            return results

        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "Directory validation")
            return results

    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            "service": "ValidationService",
            "stats": self.stats,
            "success_rate": (self.stats["successful_validations"] / max(1, self.stats["validations_performed"])) * 100
        }