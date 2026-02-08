"""
YANG Processing Module - YANG model processing and conversion
Optimal integration from additional_codes_part_2
"""
import os
import json
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

from common.handler.trace_handler import TraceHandler
from common.handler.error_handler import ErrorHandler, FormatProcessingError


class YANGProcessingModule:
    """YANG model processing with pyang integration"""

    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.stats = {
            "models_processed": 0,
            "schemas_generated": 0,
            "validations_performed": 0,
            "conversions_completed": 0
        }

    def validate_yang_model(self, yang_file: str) -> bool:
        """Validate YANG model using pyang"""
        try:
            if not os.path.exists(yang_file):
                raise FormatProcessingError(f"YANG file not found: {yang_file}")

            result = subprocess.run(
                ['pyang', '--strict', yang_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.tracer.info(f"YANG model validation successful: {yang_file}")
                self.stats["validations_performed"] += 1
                return True
            else:
                self.tracer.error(f"YANG validation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.tracer.error(f"YANG validation timeout: {yang_file}")
            return False
        except FileNotFoundError:
            self.tracer.warning("pyang not found, skipping validation")
            return True
        except Exception as e:
            self.tracer.error(f"YANG validation error: {str(e)}")
            return False

    def convert_to_json_schema(self, yang_dir: str, output_dir: str,
                              use_jar: bool = False, jar_path: Optional[str] = None) -> bool:
        """Convert YANG models to JSON Schema"""
        try:
            os.makedirs(output_dir, exist_ok=True)

            if use_jar and jar_path and os.path.exists(jar_path):
                return self._convert_with_jar(yang_dir, output_dir, jar_path)
            else:
                return self._convert_with_pyang(yang_dir, output_dir)

        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "YANG to JSON Schema conversion")
            return False

    def _convert_with_pyang(self, yang_dir: str, output_dir: str) -> bool:
        """Convert using pyang"""
        try:
            yang_files = list(Path(yang_dir).glob("*.yang"))

            for yang_file in yang_files:
                output_file = Path(output_dir) / f"{yang_file.stem}.schema.json"

                result = subprocess.run(
                    ['pyang', '-f', 'jsonschema', str(yang_file)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(result.stdout)

                    self.stats["schemas_generated"] += 1
                    self.tracer.info(f"Schema generated: {output_file}")
                else:
                    self.tracer.warning(f"Schema generation failed for {yang_file}: {result.stderr}")

            self.stats["conversions_completed"] += 1
            return True

        except FileNotFoundError:
            self.tracer.error("pyang not found - install with: pip install pyang")
            return False
        except Exception as e:
            raise FormatProcessingError(f"pyang conversion failed: {str(e)}")

    def _convert_with_jar(self, yang_dir: str, output_dir: str, jar_path: str) -> bool:
        """Convert using YANG utilities JAR"""
        try:
            result = subprocess.run([
                'java', '-jar', jar_path,
                'jsonschema-generator',
                '--files', f"{yang_dir}/*.yang",
                '--module-dirs', yang_dir,
                '--output-dir', output_dir,
                '--allow-additional-properties'
            ], capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                self.stats["schemas_generated"] += 1
                self.stats["conversions_completed"] += 1
                self.tracer.info(f"JAR-based conversion completed: {output_dir}")
                return True
            else:
                raise FormatProcessingError(f"JAR conversion failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise FormatProcessingError("JAR conversion timeout")
        except Exception as e:
            raise FormatProcessingError(f"JAR conversion failed: {str(e)}")

    def combine_schemas(self, schema_dir: str, output_file: str) -> bool:
        """Combine multiple JSON schemas into one"""
        try:
            combined_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {}
            }

            schema_files = list(Path(schema_dir).glob("*.json"))

            for schema_file in schema_files:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_content = json.load(f)

                if isinstance(schema_content, dict) and "properties" in schema_content:
                    combined_schema["properties"].update(schema_content["properties"])

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(combined_schema, f, indent=2)

            self.tracer.info(f"Schemas combined: {output_file}")
            return True

        except Exception as e:
            ErrorHandler.handle(e, self.tracer, "Schema combination")
            return False

    def validate_json_schema(self, schema_file: str, meta_schema_file: Optional[str] = None) -> bool:
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

            self.tracer.info(f"Schema validation successful: {schema_file}")
            self.stats["validations_performed"] += 1
            return True

        except Exception as e:
            self.tracer.error(f"Schema validation error: {str(e)}")
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return self.stats