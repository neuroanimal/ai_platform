"""
Enhanced Universal Validation Service
Supports validation against standards, meta-schemas, and cross-format validation
"""
import json
import yaml
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import jsonschema
from pathlib import Path

try:
    from ..conversion.universal_format_converter import UniversalFormatConverter, SupportedFormat
    from ..schema.yaml_schema_processor import YAMLSchemaProcessor, SchemaFormat
    from ..netconf.netconf_xml_processor import NetconfXMLProcessor
    CONVERTERS_AVAILABLE = True
except ImportError:
    CONVERTERS_AVAILABLE = False

class ValidationType(Enum):
    SYNTAX = "syntax"
    SCHEMA = "schema"
    STANDARD = "standard"
    CROSS_FORMAT = "cross_format"
    META_SCHEMA = "meta_schema"

class ValidationStandard(Enum):
    JSON_SCHEMA_DRAFT_07 = "json_schema_draft_07"
    YAML_SCHEMA = "yaml_schema"
    OPENAPI_3 = "openapi_3"
    ASYNCAPI_2 = "asyncapi_2"
    XML_SCHEMA = "xml_schema"
    NETCONF_RFC6241 = "netconf_rfc6241"
    YANG_RFC7950 = "yang_rfc7950"
    HELM_CHART = "helm_chart"
    TOML_SPEC = "toml_spec"

@dataclass
class ValidationResult:
    valid: bool
    validation_type: ValidationType
    format: str
    errors: List[str]
    warnings: List[str]
    standard: Optional[ValidationStandard] = None
    metadata: Optional[Dict] = None

@dataclass
class CrossFormatValidationResult:
    source_format: str
    target_format: str
    conversion_valid: bool
    data_integrity: bool
    errors: List[str]
    warnings: List[str]
    loss_report: Optional[Dict] = None

class UniversalValidationService:
    """Enhanced validation service with cross-format and standard validation"""
    
    def __init__(self):
        if CONVERTERS_AVAILABLE:
            self.converter = UniversalFormatConverter()
            self.schema_processor = YAMLSchemaProcessor()
            self.netconf_processor = NetconfXMLProcessor()
        
        self.standard_schemas = {
            ValidationStandard.JSON_SCHEMA_DRAFT_07: "http://json-schema.org/draft-07/schema#",
            ValidationStandard.OPENAPI_3: "https://spec.openapis.org/oas/v3.0.3/schema/",
            ValidationStandard.ASYNCAPI_2: "https://www.asyncapi.com/definitions/2.4.0/asyncapi.json"
        }
        
        self.format_standards = {
            'json': [ValidationStandard.JSON_SCHEMA_DRAFT_07],
            'yaml': [ValidationStandard.YAML_SCHEMA, ValidationStandard.OPENAPI_3, ValidationStandard.ASYNCAPI_2],
            'xml': [ValidationStandard.XML_SCHEMA, ValidationStandard.NETCONF_RFC6241],
            'yang': [ValidationStandard.YANG_RFC7950],
            'helm': [ValidationStandard.HELM_CHART],
            'toml': [ValidationStandard.TOML_SPEC]
        }
    
    def validate_syntax(self, file_path: str, format_type: Optional[str] = None) -> ValidationResult:
        """Validate file syntax"""
        
        if not format_type:
            format_type = self._detect_format(file_path)
        
        errors = []
        warnings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if format_type in ['json', 'json_schema', 'mrcf']:
                json.loads(content)
            elif format_type in ['yaml', 'yml', 'helm', 'yaml_schema']:
                yaml.safe_load(content)
            elif format_type in ['xml', 'netconf_xml']:
                ET.fromstring(content)
            elif format_type == 'toml':
                import toml
                toml.loads(content)
            elif format_type == 'yang':
                # Basic YANG syntax validation
                self._validate_yang_syntax(content, errors, warnings)
            
        except json.JSONDecodeError as e:
            errors.append(f"JSON syntax error: {e}")
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {e}")
        except ET.ParseError as e:
            errors.append(f"XML syntax error: {e}")
        except Exception as e:
            errors.append(f"Syntax error: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            validation_type=ValidationType.SYNTAX,
            format=format_type,
            errors=errors,
            warnings=warnings
        )
    
    def validate_against_schema(self, data_file: str, schema_file: str) -> ValidationResult:
        """Validate data against schema"""
        
        errors = []
        warnings = []
        
        try:
            # Load data and schema
            data_format = self._detect_format(data_file)
            schema_format = self._detect_format(schema_file)
            
            if CONVERTERS_AVAILABLE:
                data_result = self.converter.load_data(data_file)
                schema_result = self.converter.load_data(schema_file)
                
                if not data_result.success:
                    errors.append(f"Failed to load data: {data_result.error}")
                    return ValidationResult(False, ValidationType.SCHEMA, data_format, errors, warnings)
                
                if not schema_result.success:
                    errors.append(f"Failed to load schema: {schema_result.error}")
                    return ValidationResult(False, ValidationType.SCHEMA, data_format, errors, warnings)
                
                # Perform validation using appropriate processor
                if schema_format in ['yaml_schema', 'json_schema']:
                    validation_result = self.schema_processor.validate_data_against_schema(
                        data_result.data, schema_result.data, data_format
                    )
                    errors.extend(validation_result.errors)
                    warnings.extend(validation_result.warnings)
                else:
                    # Use jsonschema for basic validation
                    try:
                        jsonschema.validate(data_result.data, schema_result.data)
                    except jsonschema.ValidationError as e:
                        errors.append(f"Schema validation error: {e.message}")
            else:
                errors.append("Schema validation requires specialized processors")
        
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            validation_type=ValidationType.SCHEMA,
            format=data_format,
            errors=errors,
            warnings=warnings
        )
    
    def validate_against_standard(self, file_path: str, 
                                standard: ValidationStandard) -> ValidationResult:
        """Validate against industry standard"""
        
        format_type = self._detect_format(file_path)
        errors = []
        warnings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if format_type in ['json', 'mrcf']:
                    data = json.load(f)
                elif format_type in ['yaml', 'yml']:
                    data = yaml.safe_load(f)
                else:
                    data = f.read()
            
            # Validate against specific standards
            if standard == ValidationStandard.JSON_SCHEMA_DRAFT_07:
                self._validate_json_schema_draft_07(data, errors, warnings)
            elif standard == ValidationStandard.OPENAPI_3:
                self._validate_openapi_3(data, errors, warnings)
            elif standard == ValidationStandard.ASYNCAPI_2:
                self._validate_asyncapi_2(data, errors, warnings)
            elif standard == ValidationStandard.NETCONF_RFC6241:
                self._validate_netconf_rfc6241(data, errors, warnings)
            elif standard == ValidationStandard.YANG_RFC7950:
                self._validate_yang_rfc7950(data, errors, warnings)
            elif standard == ValidationStandard.HELM_CHART:
                self._validate_helm_chart(data, errors, warnings)
            elif standard == ValidationStandard.TOML_SPEC:
                self._validate_toml_spec(data, errors, warnings)
            else:
                errors.append(f"Standard validation not implemented: {standard}")
        
        except Exception as e:
            errors.append(f"Standard validation error: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            validation_type=ValidationType.STANDARD,
            format=format_type,
            errors=errors,
            warnings=warnings,
            standard=standard
        )
    
    def validate_cross_format(self, source_file: str, target_format: str) -> CrossFormatValidationResult:
        """Validate conversion between formats"""
        
        source_format = self._detect_format(source_file)
        errors = []
        warnings = []
        conversion_valid = False
        data_integrity = False
        loss_report = {}
        
        if not CONVERTERS_AVAILABLE:
            errors.append("Cross-format validation requires converters")
            return CrossFormatValidationResult(
                source_format, target_format, False, False, errors, warnings
            )
        
        try:
            # Load source data
            source_result = self.converter.load_data(source_file)
            if not source_result.success:
                errors.append(f"Failed to load source: {source_result.error}")
                return CrossFormatValidationResult(
                    source_format, target_format, False, False, errors, warnings
                )
            
            # Convert to target format
            target_format_enum = SupportedFormat(target_format)
            conversion_result = self.converter.convert(
                source_file, target_format_enum, source_format=source_result.format
            )
            
            if conversion_result.success:
                conversion_valid = True
                
                # Check data integrity by round-trip conversion
                integrity_check = self._check_data_integrity(
                    source_result.data, conversion_result.data, 
                    source_format, target_format
                )
                
                data_integrity = integrity_check['integrity']
                loss_report = integrity_check['loss_report']
                warnings.extend(integrity_check['warnings'])
            else:
                errors.append(f"Conversion failed: {conversion_result.error}")
        
        except Exception as e:
            errors.append(f"Cross-format validation error: {e}")
        
        return CrossFormatValidationResult(
            source_format=source_format,
            target_format=target_format,
            conversion_valid=conversion_valid,
            data_integrity=data_integrity,
            errors=errors,
            warnings=warnings,
            loss_report=loss_report
        )
    
    def batch_validate(self, files: List[str], 
                      validation_types: List[ValidationType]) -> List[ValidationResult]:
        """Batch validation of multiple files"""
        
        results = []
        
        for file_path in files:
            for validation_type in validation_types:
                if validation_type == ValidationType.SYNTAX:
                    result = self.validate_syntax(file_path)
                elif validation_type == ValidationType.STANDARD:
                    # Auto-detect appropriate standard
                    format_type = self._detect_format(file_path)
                    standards = self.format_standards.get(format_type, [])
                    if standards:
                        result = self.validate_against_standard(file_path, standards[0])
                    else:
                        result = ValidationResult(
                            False, validation_type, format_type, 
                            [f"No standard defined for format: {format_type}"], []
                        )
                else:
                    # Skip validation types that require additional parameters
                    continue
                
                results.append(result)
        
        return results
    
    def _detect_format(self, file_path: str) -> str:
        """Detect file format"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        format_map = {
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.xml': 'xml',
            '.xls': 'xls',
            '.xlsx': 'xlsx',
            '.csv': 'csv',
            '.tsv': 'tsv',
            '.toml': 'toml',
            '.yang': 'yang',
            '.mrcf': 'mrcf'
        }
        
        return format_map.get(ext, 'unknown')
    
    def _validate_yang_syntax(self, content: str, errors: List[str], warnings: List[str]):
        """Basic YANG syntax validation"""
        lines = content.split('\n')
        
        # Check for required module statement
        if not any('module ' in line for line in lines):
            errors.append("YANG module missing 'module' statement")
        
        # Check for balanced braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        
        # Check for semicolons
        statements = ['namespace', 'prefix', 'leaf', 'container', 'list']
        for line in lines:
            line = line.strip()
            if any(line.startswith(stmt) for stmt in statements):
                if not line.endswith(';') and not line.endswith('{'):
                    warnings.append(f"Statement may be missing semicolon: {line}")
    
    def _validate_json_schema_draft_07(self, data: Dict, errors: List[str], warnings: List[str]):
        """Validate JSON Schema Draft 07"""
        required_fields = ['$schema']
        
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        if '$schema' in data:
            if 'draft-07' not in data['$schema']:
                warnings.append("Schema does not reference Draft 07")
    
    def _validate_openapi_3(self, data: Dict, errors: List[str], warnings: List[str]):
        """Validate OpenAPI 3.x"""
        required_fields = ['openapi', 'info', 'paths']
        
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        if 'openapi' in data:
            version = data['openapi']
            if not version.startswith('3.'):
                errors.append(f"Invalid OpenAPI version: {version}")
    
    def _validate_asyncapi_2(self, data: Dict, errors: List[str], warnings: List[str]):
        """Validate AsyncAPI 2.x"""
        required_fields = ['asyncapi', 'info', 'channels']
        
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        if 'asyncapi' in data:
            version = data['asyncapi']
            if not version.startswith('2.'):
                errors.append(f"Invalid AsyncAPI version: {version}")
    
    def _validate_netconf_rfc6241(self, data: str, errors: List[str], warnings: List[str]):
        """Validate NETCONF RFC 6241"""
        if CONVERTERS_AVAILABLE and self.netconf_processor:
            try:
                session = self.netconf_processor.parse_netconf_session(data)
                for message in session.messages:
                    if message.error:
                        errors.append(f"NETCONF message error: {message.error}")
                    else:
                        validation_issues = self.netconf_processor.validate_netconf_message(message)
                        errors.extend(validation_issues)
            except Exception as e:
                errors.append(f"NETCONF validation error: {e}")
        else:
            warnings.append("NETCONF validation requires specialized processor")
    
    def _validate_yang_rfc7950(self, data: str, errors: List[str], warnings: List[str]):
        """Validate YANG RFC 7950"""
        self._validate_yang_syntax(data, errors, warnings)
        
        # Additional RFC 7950 specific checks
        if 'yang-version' not in data:
            warnings.append("YANG version not specified")
        
        if 'organization' not in data:
            warnings.append("Organization statement recommended")
    
    def _validate_helm_chart(self, data: Dict, errors: List[str], warnings: List[str]):
        """Validate Helm Chart"""
        if 'apiVersion' not in data:
            errors.append("Missing apiVersion field")
        
        if 'kind' not in data:
            errors.append("Missing kind field")
        
        if 'metadata' not in data:
            errors.append("Missing metadata field")
        elif 'name' not in data['metadata']:
            errors.append("Missing metadata.name field")
    
    def _validate_toml_spec(self, data: str, errors: List[str], warnings: List[str]):
        """Validate TOML specification"""
        try:
            import toml
            toml.loads(data)
        except Exception as e:
            errors.append(f"TOML validation error: {e}")
    
    def _check_data_integrity(self, source_data: Any, converted_data: Any, 
                            source_format: str, target_format: str) -> Dict:
        """Check data integrity after conversion"""
        
        integrity = True
        warnings = []
        loss_report = {
            'data_loss': False,
            'type_changes': [],
            'structure_changes': [],
            'precision_loss': []
        }
        
        # Compare data structures
        if isinstance(source_data, dict) and isinstance(converted_data, dict):
            source_keys = set(source_data.keys())
            converted_keys = set(converted_data.keys())
            
            missing_keys = source_keys - converted_keys
            if missing_keys:
                loss_report['data_loss'] = True
                loss_report['structure_changes'].append(f"Missing keys: {missing_keys}")
                integrity = False
            
            extra_keys = converted_keys - source_keys
            if extra_keys:
                warnings.append(f"Extra keys added during conversion: {extra_keys}")
        
        # Check for type changes
        if type(source_data) != type(converted_data):
            loss_report['type_changes'].append(
                f"Type changed from {type(source_data).__name__} to {type(converted_data).__name__}"
            )
            warnings.append("Data type changed during conversion")
        
        return {
            'integrity': integrity,
            'warnings': warnings,
            'loss_report': loss_report
        }