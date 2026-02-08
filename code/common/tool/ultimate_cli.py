"""
Ultimate CLI - Complete command-line interface with comprehensive format support
"""
import click
import json
import yaml
from enum import Enum
from pathlib import Path
from typing import Optional, List


# Import all processing modules
import sys
from pathlib import Path as PathLib

# Add project root to path for absolute imports
project_root = PathLib(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

PROCESSORS_AVAILABLE = True
MISSING_MODULES = []

try:
    from code.common.backend.service_layer.format_processing.conversion.universal_format_converter import (
        UniversalFormatConverter, SupportedFormat
    )
except ImportError as e:
    PROCESSORS_AVAILABLE = False
    MISSING_MODULES.append(f"UniversalFormatConverter: {e}")
    SupportedFormat = Enum('SupportedFormat', {})

try:
    from code.common.backend.service_layer.format_processing.excel_specialized.specialized_excel_processor import (
        SpecializedExcelProcessor, ExcelType
    )
except ImportError as e:
    PROCESSORS_AVAILABLE = False
    MISSING_MODULES.append(f"SpecializedExcelProcessor: {e}")
    ExcelType = Enum('ExcelType', {})

try:
    from code.common.backend.service_layer.format_processing.path_query.path_query_processor import (
        PathQueryProcessor, QueryType
    )
except ImportError as e:
    PROCESSORS_AVAILABLE = False
    MISSING_MODULES.append(f"PathQueryProcessor: {e}")
    QueryType = Enum('QueryType', {})

try:
    from code.common.backend.service_layer.format_processing.netconf.netconf_xml_processor import (
        NetconfXMLProcessor, NetconfOperation
    )
except ImportError as e:
    PROCESSORS_AVAILABLE = False
    MISSING_MODULES.append(f"NetconfXMLProcessor: {e}")
    NetconfOperation = Enum('NetconfOperation', {})

try:
    from code.common.backend.service_layer.format_processing.schema.yaml_schema_processor import (
        YAMLSchemaProcessor, SchemaFormat
    )
except ImportError as e:
    MISSING_MODULES.append(f"YAMLSchemaProcessor: {e}")

try:
    from code.common.backend.service_layer.format_processing.validation.universal_validation_service import (
        UniversalValidationService, ValidationType, ValidationStandard
    )
except ImportError as e:
    PROCESSORS_AVAILABLE = False
    MISSING_MODULES.append(f"UniversalValidationService: {e}")
    ValidationType = Enum('ValidationType', {})
    ValidationStandard = Enum('ValidationStandard', {})

@click.group()
@click.version_option(version='2.0.0')
def cli():
    """Ultimate AI Platform CLI - Comprehensive format processing and validation"""
    pass

@cli.group()
def convert():
    """Format conversion commands"""
    pass

@convert.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.argument('target_file', type=click.Path())
@click.option('--source-format', type=click.Choice([f.value for f in SupportedFormat]),
              help='Source format (auto-detected if not specified)')
@click.option('--target-format', type=click.Choice([f.value for f in SupportedFormat]),
              required=True, help='Target format')
def file(source_file, target_file, source_format, target_format):
    """Convert between any supported format pair"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Format converters not available")
        return

    converter = UniversalFormatConverter()

    source_format_enum = SupportedFormat(source_format) if source_format else None
    target_format_enum = SupportedFormat(target_format)

    result = converter.convert(source_file, target_format_enum, target_file, source_format_enum)

    if result.success:
        click.echo(f"✓ Converted {source_file} to {target_file}")
        if result.metadata:
            click.echo(f"  Source format: {result.metadata.get('source_format', 'auto-detected')}")
    else:
        click.echo(f"✗ Conversion failed: {result.error}")

@convert.command()
@click.argument('source_files', nargs=-1, type=click.Path(exists=True))
@click.option('--target-format', type=click.Choice([f.value for f in SupportedFormat]),
              required=True, help='Target format for all files')
@click.option('--output-dir', type=click.Path(), help='Output directory')
def batch(source_files, target_format, output_dir):
    """Batch convert multiple files to same format"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Format converters not available")
        return

    converter = UniversalFormatConverter()
    target_format_enum = SupportedFormat(target_format)

    output_path = Path(output_dir) if output_dir else Path.cwd()
    output_path.mkdir(exist_ok=True)

    for source_file in source_files:
        source_path = Path(source_file)
        target_file = output_path / f"{source_path.stem}.{target_format}"

        result = converter.convert(str(source_path), target_format_enum, str(target_file))

        if result.success:
            click.echo(f"✓ {source_file} -> {target_file}")
        else:
            click.echo(f"✗ {source_file}: {result.error}")

@cli.group()
def excel():
    """Specialized Excel processing commands"""
    pass

@excel.command()
@click.argument('excel_file', type=click.Path(exists=True))
@click.option('--excel-type', type=click.Choice([t.value for t in ExcelType]),
              help='Excel type (auto-detected if not specified)')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--format', 'output_format', default='json',
              type=click.Choice(['json', 'yaml', 'mrcf']), help='Output format')
def process(excel_file, excel_type, output, output_format):
    """Process specialized Excel files (Parameter Description, LLD, etc.)"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Excel processors not available")
        return

    processor = SpecializedExcelProcessor()
    excel_type_enum = ExcelType(excel_type) if excel_type else None

    result = processor.process_excel(excel_file, excel_type_enum)

    click.echo(f"Excel Type: {result.metadata.excel_type.value}")
    if result.metadata.product_type:
        click.echo(f"Product: {result.metadata.product_type.value}")
    if result.metadata.deployment_day:
        click.echo(f"Deployment Day: {result.metadata.deployment_day.value}")

    click.echo(f"Processed {len(result.data)} rows")

    for validation in result.validation_results:
        click.echo(f"Validation: {validation}")

    if output:
        if output_format == 'mrcf':
            mrcf_data = processor.convert_to_mrcf(result)
            with open(output, 'w') as f:
                json.dump(mrcf_data, f, indent=2)
        elif output_format == 'yaml':
            with open(output, 'w') as f:
                yaml.dump(result.data.to_dict('records'), f)
        else:
            result.data.to_json(output, indent=2)

        click.echo(f"Output saved to {output}")

@cli.group()
def query():
    """Path query commands (JSONPath, XPath)"""
    pass

@query.command()
@click.argument('data_file', type=click.Path(exists=True))
@click.argument('query_expression')
@click.option('--query-type', type=click.Choice([t.value for t in QueryType]),
              default='jsonpath', help='Query type')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def path(data_file, query_expression, query_type, output):
    """Query data using JSONPath, JSONPathExt, or XPath"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Path query processors not available")
        return

    processor = PathQueryProcessor()
    query_type_enum = QueryType(query_type)

    # Load data
    with open(data_file, 'r') as f:
        if data_file.endswith(('.xml', '.netconf')):
            data = f.read()
            result = processor.query_xml(data, query_expression)
        else:
            data = f.read()
            result = processor.query_json(data, query_expression, query_type_enum)

    if result.success:
        click.echo(f"Query: {result.query}")
        click.echo(f"Results ({len(result.results)}):")

        for i, res in enumerate(result.results):
            click.echo(f"  [{i}]: {res}")

        if result.metadata:
            click.echo(f"Metadata: {result.metadata}")

        if output:
            with open(output, 'w') as f:
                json.dump(result.results, f, indent=2)
            click.echo(f"Results saved to {output}")
    else:
        click.echo(f"Query failed: {result.error}")

@query.command()
@click.argument('data_file', type=click.Path(exists=True))
@click.option('--data-type', type=click.Choice(['json', 'xml']), default='json')
def paths(data_file, data_type):
    """List all available paths in data structure"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Path query processors not available")
        return

    processor = PathQueryProcessor()

    with open(data_file, 'r') as f:
        if data_type == 'xml':
            import xml.etree.ElementTree as ET
            data = ET.fromstring(f.read())
        else:
            data = json.load(f)

    all_paths = processor.find_all_paths(data, data_type)

    click.echo(f"Available paths ({len(all_paths)}):")
    for path in sorted(all_paths):
        click.echo(f"  {path}")

@cli.group()
def netconf():
    """NETCONF XML processing commands"""
    pass

@netconf.command()
@click.argument('session_file', type=click.Path(exists=True))
@click.option('--version', default='1.0', type=click.Choice(['1.0', '1.1']),
              help='NETCONF version')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def parse(session_file, version, output):
    """Parse NETCONF session file"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: NETCONF processors not available")
        return

    processor = NetconfXMLProcessor()

    with open(session_file, 'r') as f:
        session_data = f.read()

    session = processor.parse_netconf_session(session_data, version)

    click.echo(f"NETCONF Session (v{session.protocol_version})")
    click.echo(f"Session ID: {session.session_id}")
    click.echo(f"Messages: {len(session.messages)}")
    click.echo(f"Capabilities: {len(session.capabilities)}")

    for i, message in enumerate(session.messages):
        click.echo(f"\nMessage {i+1}:")
        click.echo(f"  ID: {message.message_id}")
        click.echo(f"  Operation: {message.operation}")
        click.echo(f"  RPC: {message.is_rpc}, Reply: {message.is_reply}")
        if message.error:
            click.echo(f"  Error: {message.error}")

    if output:
        session_dict = {
            'session_id': session.session_id,
            'version': session.protocol_version,
            'capabilities': session.capabilities,
            'messages': [
                {
                    'message_id': msg.message_id,
                    'operation': msg.operation.value if msg.operation else None,
                    'is_rpc': msg.is_rpc,
                    'is_reply': msg.is_reply,
                    'error': msg.error
                }
                for msg in session.messages
            ]
        }

        with open(output, 'w') as f:
            json.dump(session_dict, f, indent=2)

        click.echo(f"Session data saved to {output}")

@netconf.command()
@click.option('--operation', type=click.Choice([op.value for op in NetconfOperation]),
              required=True, help='NETCONF operation')
@click.option('--message-id', required=True, help='Message ID')
@click.option('--target', default='candidate', help='Target datastore')
@click.option('--source', default='running', help='Source datastore')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def create_rpc(operation, message_id, target, source, output):
    """Create NETCONF RPC message"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: NETCONF processors not available")
        return

    processor = NetconfXMLProcessor()
    operation_enum = NetconfOperation(operation)

    rpc_xml = processor.create_netconf_rpc(
        operation_enum, message_id, target=target, source=source
    )

    if output:
        with open(output, 'w') as f:
            f.write(rpc_xml)
        click.echo(f"RPC saved to {output}")
    else:
        click.echo(rpc_xml)

@cli.group()
def validate():
    """Validation commands"""
    pass

@validate.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--format', 'file_format', help='File format (auto-detected if not specified)')
def syntax(file_path, file_format):
    """Validate file syntax"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Validation services not available")
        return

    validator = UniversalValidationService()
    result = validator.validate_syntax(file_path, file_format)

    if result.valid:
        click.echo(f"✓ Syntax valid ({result.format})")
    else:
        click.echo(f"✗ Syntax errors in {result.format}:")
        for error in result.errors:
            click.echo(f"  - {error}")

    for warning in result.warnings:
        click.echo(f"  Warning: {warning}")

@validate.command()
@click.argument('data_file', type=click.Path(exists=True))
@click.argument('schema_file', type=click.Path(exists=True))
def schema(data_file, schema_file):
    """Validate data against schema"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Validation services not available")
        return

    validator = UniversalValidationService()
    result = validator.validate_against_schema(data_file, schema_file)

    if result.valid:
        click.echo(f"✓ Schema validation passed ({result.format})")
    else:
        click.echo(f"✗ Schema validation failed ({result.format}):")
        for error in result.errors:
            click.echo(f"  - {error}")

    for warning in result.warnings:
        click.echo(f"  Warning: {warning}")

@validate.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--standard', type=click.Choice([s.value for s in ValidationStandard]),
              required=True, help='Validation standard')
def standard(file_path, standard):
    """Validate against industry standard"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Validation services not available")
        return

    validator = UniversalValidationService()
    standard_enum = ValidationStandard(standard)
    result = validator.validate_against_standard(file_path, standard_enum)

    if result.valid:
        click.echo(f"✓ Standard validation passed ({standard})")
    else:
        click.echo(f"✗ Standard validation failed ({standard}):")
        for error in result.errors:
            click.echo(f"  - {error}")

    for warning in result.warnings:
        click.echo(f"  Warning: {warning}")

@validate.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--target-format', type=click.Choice([f.value for f in SupportedFormat]),
              required=True, help='Target format for conversion validation')
def cross_format(source_file, target_format):
    """Validate cross-format conversion"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Validation services not available")
        return

    validator = UniversalValidationService()
    result = validator.validate_cross_format(source_file, target_format)

    click.echo(f"Cross-format validation: {result.source_format} -> {result.target_format}")

    if result.conversion_valid:
        click.echo("✓ Conversion successful")
    else:
        click.echo("✗ Conversion failed")

    if result.data_integrity:
        click.echo("✓ Data integrity maintained")
    else:
        click.echo("✗ Data integrity issues")
        if result.loss_report:
            click.echo("Loss report:")
            for key, value in result.loss_report.items():
                if value:
                    click.echo(f"  {key}: {value}")

    for error in result.errors:
        click.echo(f"  Error: {error}")

    for warning in result.warnings:
        click.echo(f"  Warning: {warning}")

@validate.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option('--validation-types', multiple=True,
              type=click.Choice([t.value for t in ValidationType]),
              default=['syntax'], help='Validation types to perform')
def batch(files, validation_types):
    """Batch validate multiple files"""
    if not PROCESSORS_AVAILABLE:
        click.echo("Error: Validation services not available")
        return

    validator = UniversalValidationService()
    validation_types_enum = [ValidationType(vt) for vt in validation_types]

    results = validator.batch_validate(list(files), validation_types_enum)

    click.echo(f"Batch validation results ({len(results)} validations):")

    for result in results:
        status = "✓" if result.valid else "✗"
        click.echo(f"{status} {result.validation_type.value}: {result.format}")

        if result.errors:
            for error in result.errors[:3]:  # Show first 3 errors
                click.echo(f"    - {error}")
            if len(result.errors) > 3:
                click.echo(f"    ... and {len(result.errors) - 3} more errors")

@cli.group()
def yang():
    """YANG model processing commands"""
    pass

@yang.command()
@click.argument('yang_path', type=click.Path(exists=True))
@click.option('--strict', is_flag=True, help='Use pyang for strict validation')
@click.option('--jar', type=click.Path(exists=True), help='Path to YANG utilities JAR file')
@click.option('--max-warnings', default=100, type=int, help='Maximum warnings to display per file (default: 100)')
def validate(yang_path, strict, jar, max_warnings):
    """Validate YANG model file or directory"""
    import re

    def validate_yang_basic(file_path):
        """Basic regex validation"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            content_no_comments = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            content_no_comments = re.sub(r'/\*.*?\*/', '', content_no_comments, flags=re.DOTALL)
            content_no_comments = re.sub(r'\s+', ' ', content_no_comments)

            module_match = re.search(r'\b(module|submodule)\s+([\w-]+)\s*\{', content_no_comments)
            if not module_match:
                errors.append("Missing module/submodule declaration")
                return errors

            is_module = module_match.group(1) == 'module'

            if is_module:
                if not re.search(r'\bnamespace\s+["\']?[^;]+["\']?\s*;', content_no_comments):
                    errors.append("Missing namespace statement")
                if not re.search(r'\bprefix\s+["\']?[\w-]+["\']?\s*;', content_no_comments):
                    errors.append("Missing prefix statement")

            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces != close_braces:
                errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")

            return errors
        except Exception as e:
            return [str(e)]

    def validate_yang_pyang(file_path, yang_dir):
        """Strict validation using pyang"""
        try:
            import pyang
            from pyang import context, repository

            repos = repository.FileRepository(str(yang_dir))
            ctx = context.Context(repos)

            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            module = ctx.add_module(str(file_path), text)

            if module is None:
                return [], ["Failed to parse module"], {}

            ctx.validate()

            errors = []
            warnings = []
            fixes = {}
            seen_messages = set()  # Track unique messages

            for epos, etag, eargs in ctx.errors:
                if eargs:
                    args_str = ''.join(str(arg) for arg in eargs)
                else:
                    args_str = ''
                msg = f"Line {epos.line}: {etag} - {args_str}" if args_str else f"Line {epos.line}: {etag}"

                # Skip duplicates
                if msg in seen_messages:
                    continue
                seen_messages.add(msg)

                if etag == 'UNUSED_IMPORT':
                    warnings.append(msg)
                elif etag == 'REVISION_ORDER':
                    # Treat as warning - revisions should be in reverse chronological order
                    warnings.append(msg + " (revisions should be newest first)")
                elif etag == 'WPREFIX_NOT_DEFINED':
                    # Find which module defines this prefix
                    undefined_prefix = args_str
                    suggested_module = find_module_for_prefix(undefined_prefix, yang_dir)
                    if suggested_module:
                        fixes[msg] = f"Add: import {suggested_module} {{ prefix {undefined_prefix}; }}"
                    errors.append(msg)
                else:
                    errors.append(msg)

            return errors, warnings, fixes
        except ImportError:
            return ["pyang not installed. Install with: pip install pyang"], [], {}
        except Exception as e:
            return [f"pyang error: {str(e)}"], [], {}

    def validate_yang_jar(file_path, jar_path, yang_dir):
        """Validation using external YANG utilities JAR"""
        import subprocess
        import json
        import re
        try:
            cmd = ['java', '-jar', str(jar_path), 'yangval', '--files', str(file_path), '--module-dirs', str(yang_dir), '--yanglint']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            errors = []
            warnings = []
            fixes = {}

            output = result.stdout + result.stderr

            # Extract detailed report URL and reqid
            report_url = None
            reqid = None
            url_match = re.search(r'"Detailed report is available at"\s*:\s*"([^"]+)"', output)
            if url_match:
                report_url = url_match.group(1)
                reqid_match = re.search(r'reqid=(\d+)', report_url)
                if reqid_match:
                    reqid = reqid_match.group(1)

            # Extract error/warning counts from summary
            error_count = 0
            warning_count = 0
            if '"ERROR"' in output:
                match = re.search(r'"ERROR"\s*:\s*(\d+)', output)
                if match:
                    error_count = int(match.group(1))
            if '"WARNING"' in output:
                match = re.search(r'"WARNING"\s*:\s*(\d+)', output)
                if match:
                    warning_count = int(match.group(1))

            # Extract actual error/warning messages from output
            for line in output.split('\n'):
                line = line.strip()
                if not line or line.startswith('{') or line.startswith('}') or '"Validation' in line or '"YangVal' in line or '"Detailed report' in line or '"Applied filters' in line:
                    continue
                if line.startswith('[') and 'ERROR' in line:
                    errors.append(line)
                elif line.startswith('[') and ('WARNING' in line or 'WARN' in line):
                    warnings.append(line)

            # If counts indicate issues but no messages, fetch from JSON report
            if reqid and ((error_count > 0 and not errors) or (warning_count > 0 and not warnings)):
                try:
                    import urllib.request
                    json_url = f"https://yang-dashboard.swe.cig.company.es/api/proj-yangtooling-generic-local/detailed-results/{reqid}.json"
                    with urllib.request.urlopen(json_url, timeout=10) as response:
                        json_data = json.loads(response.read())
                        for item in json_data:
                            severity = item.get('severity', '')
                            source = item.get('source', '')
                            resource = item.get('resource', '')
                            line_no = item.get('lineNo', '')
                            message = item.get('message', '')
                            msg = f"[{source}] {severity} {resource}:{line_no} {message}"
                            if severity == 'ERROR':
                                errors.append(msg)
                            elif severity == 'WARNING':
                                warnings.append(msg)
                except:
                    pass

            # If still no messages, add summary
            if error_count > 0 and not errors:
                if report_url:
                    errors.append(f"{error_count} error(s) found - see report for details")
                else:
                    errors.append(f"{error_count} error(s) found")
            if warning_count > 0 and not warnings:
                warnings.append(f"{warning_count} warning(s) found")

            # Add report URL to fixes if available
            if report_url:
                fixes['_report_url'] = report_url

            return errors, warnings, fixes
        except subprocess.TimeoutExpired:
            return ["Validation timeout (60s)"], [], {}
        except FileNotFoundError:
            return ["Java not found. Install Java to use JAR validation."], [], {}
        except Exception as e:
            return [f"JAR validation error: {str(e)}"], [], {}

    def find_module_for_prefix(prefix, yang_dir):
        """Find which YANG module defines the given prefix"""
        import re
        for yang_file in Path(yang_dir).glob('*.yang'):
            try:
                with open(yang_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Look for: module <name> { ... prefix <prefix>;
                if re.search(rf'module\s+([\w-]+)\s*\{{[^}}]*prefix\s+["\']?{re.escape(prefix)}["\']?\s*;', content, re.DOTALL):
                    match = re.search(r'module\s+([\w-]+)', content)
                    if match:
                        return match.group(1)
            except:
                pass
        return None

    path = Path(yang_path)
    yang_files = [path] if path.is_file() else list(path.glob('**/*.yang'))
    yang_dir = path.parent if path.is_file() else path

    if not yang_files:
        click.echo(f"✗ No YANG files found in {yang_path}")
        return

    if jar:
        mode = "jar"
    elif strict:
        mode = "pyang"
    else:
        mode = "basic"
    click.echo(f"Validating {len(yang_files)} YANG file(s) [{mode}]...")
    total_errors = 0
    total_warnings = 0
    passed = 0

    for yang_file in yang_files:
        if jar:
            errors, warnings, fixes = validate_yang_jar(yang_file, jar, yang_dir)
        elif strict:
            errors, warnings, fixes = validate_yang_pyang(yang_file, yang_dir)
        else:
            errors = validate_yang_basic(yang_file)
            warnings = []
            fixes = {}

        if not errors and not warnings:
            click.echo(f"  ✓ [OK] {yang_file.name}")
            passed += 1
        else:
            click.echo(f"  ✗ [NOK] {yang_file.name}:")

            # Show detailed report URL if available
            if '_report_url' in fixes:
                click.echo(f"      📊 Report: {fixes['_report_url']}")

            # Show all errors
            for error in errors:
                click.echo(f"      ❌ [ERROR] {error}")
                if error in fixes:
                    click.echo(f"          → FIX: {fixes[error]}")
            total_errors += len(errors)

            # Show warnings up to max_warnings limit
            for warning in warnings[:max_warnings]:
                click.echo(f"      ⚠ [WARNING] {warning}")
            if len(warnings) > max_warnings:
                click.echo(f"      ... and {len(warnings) - max_warnings} more warnings")
            total_warnings += len(warnings)

            if not errors:
                passed += 1

    click.echo(f"\nSummary: {passed}/{len(yang_files)} passed, {total_errors} errors, {total_warnings} warnings")

if __name__ == '__main__':
    cli()