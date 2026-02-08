"""
Universal Format Converter - Supports conversion between all format pairs
"""
import json
import yaml
import csv
import xml.etree.ElementTree as ET
import pandas as pd
import toml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Import specialized processors
try:
    from ..excel_specialized.specialized_excel_processor import SpecializedExcelProcessor, ExcelType
    from ..path_query.path_query_processor import PathQueryProcessor
    from ..netconf.netconf_xml_processor import NetconfXMLProcessor
    from ..schema.yaml_schema_processor import YAMLSchemaProcessor
    SPECIALIZED_PROCESSORS_AVAILABLE = True
except ImportError:
    SPECIALIZED_PROCESSORS_AVAILABLE = False

class SupportedFormat(Enum):
    YAML = "yaml"
    HELM = "helm"
    XML = "xml"
    JSON = "json"
    JSON_SCHEMA = "json_schema"
    YAML_SCHEMA = "yaml_schema"
    XLS = "xls"
    XLSX = "xlsx"
    CSV = "csv"
    TSV = "tsv"
    TOML = "toml"
    YANG = "yang"
    MRCF = "mrcf"
    NETCONF_XML = "netconf_xml"

@dataclass
class ConversionResult:
    success: bool
    data: Any
    format: SupportedFormat
    error: Optional[str] = None
    metadata: Optional[Dict] = None

class UniversalFormatConverter:
    """Universal converter supporting all format pairs"""

    def __init__(self):
        self.format_extensions = {
            '.yml': SupportedFormat.YAML,
            '.yaml': SupportedFormat.YAML,
            '.json': SupportedFormat.JSON,
            '.xml': SupportedFormat.XML,
            '.xls': SupportedFormat.XLS,
            '.xlsx': SupportedFormat.XLSX,
            '.csv': SupportedFormat.CSV,
            '.tsv': SupportedFormat.TSV,
            '.toml': SupportedFormat.TOML,
            '.yang': SupportedFormat.YANG,
            '.mrcf': SupportedFormat.MRCF
        }

        # Initialize specialized processors
        if SPECIALIZED_PROCESSORS_AVAILABLE:
            self.excel_processor = SpecializedExcelProcessor()
            self.path_processor = PathQueryProcessor()
            self.netconf_processor = NetconfXMLProcessor()
            self.schema_processor = YAMLSchemaProcessor()
        else:
            self.excel_processor = None
            self.path_processor = None
            self.netconf_processor = None
            self.schema_processor = None

    def detect_format(self, file_path: str) -> SupportedFormat:
        """Auto-detect format from file extension or content"""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext in self.format_extensions:
            return self.format_extensions[ext]

        # Content-based detection for ambiguous cases
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('<?xml'):
                    return SupportedFormat.NETCONF_XML if 'netconf' in content.lower() else SupportedFormat.XML
                elif content.startswith(('apiVersion:', 'kind:')):
                    return SupportedFormat.HELM
        except:
            pass

        return SupportedFormat.JSON  # Default fallback

    def load_data(self, file_path: str, format_type: Optional[SupportedFormat] = None) -> ConversionResult:
        """Load data from any supported format"""
        if not format_type:
            format_type = self.detect_format(file_path)

        try:
            if format_type in [SupportedFormat.YAML, SupportedFormat.HELM]:
                return self._load_yaml(file_path, format_type)
            elif format_type == SupportedFormat.JSON:
                return self._load_json(file_path)
            elif format_type in [SupportedFormat.XML, SupportedFormat.NETCONF_XML]:
                return self._load_xml(file_path, format_type)
            elif format_type in [SupportedFormat.XLS, SupportedFormat.XLSX]:
                return self._load_excel(file_path, format_type)
            elif format_type in [SupportedFormat.CSV, SupportedFormat.TSV]:
                return self._load_csv(file_path, format_type)
            elif format_type == SupportedFormat.TOML:
                return self._load_toml(file_path)
            elif format_type == SupportedFormat.YANG:
                return self._load_yang(file_path)
            elif format_type == SupportedFormat.MRCF:
                return self._load_mrcf(file_path)
            elif format_type in [SupportedFormat.JSON_SCHEMA, SupportedFormat.YAML_SCHEMA]:
                return self._load_schema(file_path, format_type)
            else:
                return ConversionResult(False, None, format_type, f"Unsupported format: {format_type}")
        except Exception as e:
            return ConversionResult(False, None, format_type, str(e))

    def convert(self, source_path: str, target_format: SupportedFormat,
                target_path: Optional[str] = None, source_format: Optional[SupportedFormat] = None) -> ConversionResult:
        """Convert between any supported format pair"""

        # Load source data
        source_result = self.load_data(source_path, source_format)
        if not source_result.success:
            return source_result

        # Convert to target format
        try:
            converted_data = self._convert_data(source_result.data, source_result.format, target_format)

            if target_path:
                self._save_data(converted_data, target_path, target_format)

            return ConversionResult(True, converted_data, target_format,
                                  metadata={'source_format': source_result.format.value})
        except Exception as e:
            return ConversionResult(False, None, target_format, str(e))

    def _convert_data(self, data: Any, source_format: SupportedFormat, target_format: SupportedFormat) -> Any:
        """Core conversion logic between formats"""

        # Normalize to intermediate representation
        normalized = self._normalize_to_dict(data, source_format)

        # Convert from normalized to target
        return self._denormalize_from_dict(normalized, target_format)

    def _normalize_to_dict(self, data: Any, format_type: SupportedFormat) -> Dict:
        """Convert any format to normalized dictionary representation"""
        if format_type in [SupportedFormat.YAML, SupportedFormat.HELM, SupportedFormat.JSON,
                          SupportedFormat.JSON_SCHEMA, SupportedFormat.YAML_SCHEMA, SupportedFormat.TOML]:
            return data if isinstance(data, dict) else {'data': data}

        elif format_type in [SupportedFormat.CSV, SupportedFormat.TSV, SupportedFormat.XLS, SupportedFormat.XLSX]:
            if isinstance(data, pd.DataFrame):
                return {'table_data': data.to_dict('records'), 'columns': data.columns.tolist()}
            return {'data': data}

        elif format_type in [SupportedFormat.XML, SupportedFormat.NETCONF_XML]:
            return self._xml_to_dict(data)

        elif format_type == SupportedFormat.MRCF:
            return data if isinstance(data, dict) else {'mrcf_data': data}

        elif format_type == SupportedFormat.YANG:
            return {'yang_model': data}

        return {'data': data}

    def _denormalize_from_dict(self, data: Dict, target_format: SupportedFormat) -> Any:
        """Convert normalized dictionary to target format"""
        if target_format in [SupportedFormat.YAML, SupportedFormat.HELM]:
            return data

        elif target_format == SupportedFormat.JSON:
            return data

        elif target_format in [SupportedFormat.JSON_SCHEMA, SupportedFormat.YAML_SCHEMA]:
            return self._generate_schema(data, target_format)

        elif target_format in [SupportedFormat.CSV, SupportedFormat.TSV]:
            return self._dict_to_csv(data, target_format)

        elif target_format in [SupportedFormat.XLS, SupportedFormat.XLSX]:
            return self._dict_to_excel(data)

        elif target_format in [SupportedFormat.XML, SupportedFormat.NETCONF_XML]:
            return self._dict_to_xml(data, target_format)

        elif target_format == SupportedFormat.TOML:
            return data

        elif target_format == SupportedFormat.MRCF:
            return self._dict_to_mrcf(data)

        elif target_format == SupportedFormat.YANG:
            return self._dict_to_yang(data)

        return data

    def _load_yaml(self, file_path: str, format_type: SupportedFormat) -> ConversionResult:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return ConversionResult(True, data, format_type)

    def _load_json(self, file_path: str) -> ConversionResult:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ConversionResult(True, data, SupportedFormat.JSON)

    def _load_xml(self, file_path: str, format_type: SupportedFormat) -> ConversionResult:
        tree = ET.parse(file_path)
        root = tree.getroot()
        return ConversionResult(True, root, format_type)

    def _load_excel(self, file_path: str, format_type: SupportedFormat) -> ConversionResult:
        df = pd.read_excel(file_path)
        return ConversionResult(True, df, format_type)

    def _load_csv(self, file_path: str, format_type: SupportedFormat) -> ConversionResult:
        delimiter = '\t' if format_type == SupportedFormat.TSV else ','
        df = pd.read_csv(file_path, delimiter=delimiter)
        return ConversionResult(True, df, format_type)

    def _load_toml(self, file_path: str) -> ConversionResult:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        return ConversionResult(True, data, SupportedFormat.TOML)

    def _load_yang(self, file_path: str) -> ConversionResult:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        return ConversionResult(True, data, SupportedFormat.YANG)

    def _load_mrcf(self, file_path: str) -> ConversionResult:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ConversionResult(True, data, SupportedFormat.MRCF)

    def _load_schema(self, file_path: str, format_type: SupportedFormat) -> ConversionResult:
        if format_type == SupportedFormat.JSON_SCHEMA:
            return self._load_json(file_path)
        else:  # YAML_SCHEMA
            return self._load_yaml(file_path, format_type)

    def _save_data(self, data: Any, file_path: str, format_type: SupportedFormat):
        """Save data in specified format"""
        if format_type in [SupportedFormat.YAML, SupportedFormat.HELM, SupportedFormat.YAML_SCHEMA]:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)

        elif format_type in [SupportedFormat.JSON, SupportedFormat.JSON_SCHEMA, SupportedFormat.MRCF]:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        elif format_type == SupportedFormat.TOML:
            with open(file_path, 'w', encoding='utf-8') as f:
                toml.dump(data, f)

        elif format_type in [SupportedFormat.CSV, SupportedFormat.TSV]:
            delimiter = '\t' if format_type == SupportedFormat.TSV else ','
            if isinstance(data, pd.DataFrame):
                data.to_csv(file_path, sep=delimiter, index=False)
            else:
                df = pd.DataFrame(data)
                df.to_csv(file_path, sep=delimiter, index=False)

        elif format_type in [SupportedFormat.XLS, SupportedFormat.XLSX]:
            if isinstance(data, pd.DataFrame):
                data.to_excel(file_path, index=False)
            else:
                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)

    def _xml_to_dict(self, element) -> Dict:
        """Convert XML element to dictionary"""
        result = {}
        if element.attrib:
            result['@attributes'] = element.attrib
        if element.text and element.text.strip():
            result['text'] = element.text.strip()
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        return result

    def _dict_to_xml(self, data: Dict, format_type: SupportedFormat) -> ET.Element:
        """Convert dictionary to XML element"""
        root = ET.Element('root')
        self._dict_to_xml_recursive(data, root)

        if format_type == SupportedFormat.NETCONF_XML:
            # Add NETCONF wrapper
            netconf_root = ET.Element('rpc', {'xmlns': 'urn:ietf:params:xml:ns:netconf:base:1.0'})
            netconf_root.append(root)
            return netconf_root

        return root

    def _dict_to_xml_recursive(self, data: Any, parent: ET.Element):
        """Recursively convert dictionary to XML"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == '@attributes':
                    parent.attrib.update(value)
                elif key == 'text':
                    parent.text = str(value)
                else:
                    child = ET.SubElement(parent, key)
                    self._dict_to_xml_recursive(value, child)
        elif isinstance(data, list):
            for item in data:
                self._dict_to_xml_recursive(item, parent)
        else:
            parent.text = str(data)

    def _generate_schema(self, data: Dict, schema_format: SupportedFormat) -> Dict:
        """Generate JSON/YAML schema from data"""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {}
        }

        for key, value in data.items():
            schema["properties"][key] = self._infer_schema_type(value)

        return schema

    def _infer_schema_type(self, value: Any) -> Dict:
        """Infer schema type from value"""
        if isinstance(value, str):
            return {"type": "string"}
        elif isinstance(value, int):
            return {"type": "integer"}
        elif isinstance(value, float):
            return {"type": "number"}
        elif isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, list):
            return {"type": "array", "items": self._infer_schema_type(value[0]) if value else {}}
        elif isinstance(value, dict):
            return {"type": "object", "properties": {k: self._infer_schema_type(v) for k, v in value.items()}}
        else:
            return {"type": "string"}

    def _dict_to_csv(self, data: Dict, format_type: SupportedFormat) -> pd.DataFrame:
        """Convert dictionary to CSV/TSV DataFrame"""
        if 'table_data' in data:
            return pd.DataFrame(data['table_data'])
        else:
            # Flatten dictionary for CSV
            flattened = self._flatten_dict(data)
            return pd.DataFrame([flattened])

    def _flatten_dict(self, data: Dict, prefix: str = '') -> Dict:
        """Flatten nested dictionary for CSV conversion"""
        result = {}
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, new_key))
            else:
                result[new_key] = value
        return result

    def _dict_to_excel(self, data: Dict) -> pd.DataFrame:
        """Convert dictionary to Excel DataFrame"""
        return self._dict_to_csv(data, SupportedFormat.CSV)

    def _dict_to_mrcf(self, data: Dict) -> Dict:
        """Convert dictionary to MRCF format"""
        mrcf_data = {}
        for key, value in data.items():
            mrcf_data[key] = {
                "description": f"Field {key}",
                "mandatory": "optional",
                "format": self._infer_mrcf_format(value),
                "type": type(value).__name__,
                "value": value
            }
        return mrcf_data

    def _infer_mrcf_format(self, value: Any) -> str:
        """Infer MRCF format from value"""
        if isinstance(value, str):
            return "string"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"

    def _dict_to_yang(self, data: Dict) -> str:
        """Convert dictionary to YANG model (basic structure)"""
        yang_content = "module generated-model {\n"
        yang_content += "  namespace \"http://example.com/generated\";\n"
        yang_content += "  prefix \"gen\";\n\n"

        for key, value in data.items():
            yang_content += f"  leaf {key} {{\n"
            yang_content += f"    type {self._infer_yang_type(value)};\n"
            yang_content += "  }\n"

        yang_content += "}\n"
        return yang_content

    def _infer_yang_type(self, value: Any) -> str:
        """Infer YANG type from value"""
        if isinstance(value, str):
            return "string"
        elif isinstance(value, int):
            return "int32"
        elif isinstance(value, float):
            return "decimal64"
        elif isinstance(value, bool):
            return "boolean"
        else:
            return "string"