"""
Format Conversion Service - Universal format conversion utilities
Optimal integration from additional_codes_part_1
"""
import json
import yaml
import pandas as pd
from typing import Dict, Any, Optional, Union
from pathlib import Path

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError
from common.engine.io_engine.yaml_io_module import YAMLIOModule
from common.engine.io_engine.json_io_module import JSONIOModule
from common.engine.io_engine.excel_io_module import ExcelIOModule


class FormatConversionService:
    """Universal format conversion service"""

    def __init__(self, product: str = "AI_Platform", version: str = "1.0"):
        self.product = product
        self.version = version
        self.tracer = TraceHandler(product, version, "FormatConverter")

        # Initialize IO modules
        self.yaml_io = YAMLIOModule(self.tracer)
        self.json_io = JSONIOModule(self.tracer)
        self.excel_io = ExcelIOModule(self.tracer)

        self.stats = {
            "conversions_performed": 0,
            "json_to_yaml": 0,
            "yaml_to_json": 0,
            "excel_to_csv": 0
        }

    def convert_file(self, input_path: str, output_path: str,
                    source_format: Optional[str] = None,
                    target_format: Optional[str] = None) -> bool:
        """Convert file from one format to another"""
        try:
            # Auto-detect formats if not provided
            if not source_format:
                source_format = self._detect_format(input_path)
            if not target_format:
                target_format = self._detect_format(output_path)

            self.tracer.info(f"Converting {source_format} to {target_format}: {input_path} -> {output_path}")

            # Route to appropriate conversion method
            conversion_key = f"{source_format}_to_{target_format}"

            if conversion_key == "json_to_yaml":
                return self._json_to_yaml(input_path, output_path)
            elif conversion_key == "yaml_to_json":
                return self._yaml_to_json(input_path, output_path)
            elif conversion_key == "excel_to_csv":
                return self._excel_to_csv(input_path, output_path)
            else:
                raise FormatProcessingError(f"Conversion {conversion_key} not supported")

        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "Format conversion")
            return False

    def _json_to_yaml(self, json_path: str, yaml_path: str) -> bool:
        """Convert JSON to YAML"""
        try:
            data = self.json_io.read_file(json_path)
            success = self.yaml_io.write_file(data, yaml_path)

            if success:
                self.stats["json_to_yaml"] += 1
                self.stats["conversions_performed"] += 1

            return success

        except Exception as e:
            raise FormatProcessingError(f"JSON to YAML conversion failed: {str(e)}")

    def _yaml_to_json(self, yaml_path: str, json_path: str) -> bool:
        """Convert YAML to JSON"""
        try:
            data = self.yaml_io.read_file(yaml_path)
            success = self.json_io.write_file(data, json_path)

            if success:
                self.stats["yaml_to_json"] += 1
                self.stats["conversions_performed"] += 1

            return success

        except Exception as e:
            raise FormatProcessingError(f"YAML to JSON conversion failed: {str(e)}")

    def _excel_to_csv(self, excel_path: str, output_dir: str) -> bool:
        """Convert Excel to CSV files"""
        try:
            results = self.excel_io.extract_tables(excel_path, output_dir)

            if results:
                self.stats["excel_to_csv"] += 1
                self.stats["conversions_performed"] += 1
                return True

            return False

        except Exception as e:
            raise FormatProcessingError(f"Excel to CSV conversion failed: {str(e)}")

    def _detect_format(self, file_path: str) -> str:
        """Auto-detect file format from extension"""
        suffix = Path(file_path).suffix.lower()

        format_map = {
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.csv': 'csv'
        }

        return format_map.get(suffix, 'unknown')

    def get_summary(self) -> Dict[str, Any]:
        """Get conversion summary"""
        return {
            "service": "FormatConversionService",
            "stats": self.stats
        }