"""
Enhanced Unified CLI - Extended with Excel and conversion support
"""
import argparse
import sys
import os
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.engine.unified_orchestrator_engine import UnifiedOrchestratorEngine, ProcessingMode
from backend.service_layer.format_processing.conversion.format_conversion_service import FormatConversionService
from common.engine.io_engine.excel_io_module import ExcelIOModule
from common.handler.trace_handler import TraceHandler


class EnhancedUnifiedCLI:
    """Enhanced CLI with Excel and conversion support"""

    def __init__(self):
        self.orchestrator = None
        self.conversion_service = None
        self.tracer = None

    def create_parser(self) -> argparse.ArgumentParser:
        """Create enhanced argument parser"""
        parser = argparse.ArgumentParser(
            description='AI Platform - Enhanced Unified CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Format Conversion
  python enhanced_cli.py convert input.json output.yaml
  python enhanced_cli.py convert input.xlsx output_dir/ --target csv

  # Excel Processing
  python enhanced_cli.py excel extract input.xlsx output_dir/
  python enhanced_cli.py excel validate input.xlsx

  # YAML Processing (existing)
  python enhanced_cli.py yaml process input.yaml --output output.yaml --mode hybrid
            """
        )

        # Global arguments
        parser.add_argument('--product', default='AI_Platform', help='Product name')
        parser.add_argument('--version', default='1.0', help='Version')
        parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Format conversion commands
        convert_parser = subparsers.add_parser('convert', help='Format conversion commands')
        convert_parser.add_argument('input', help='Input file')
        convert_parser.add_argument('output', help='Output file or directory')
        convert_parser.add_argument('--source', help='Source format (auto-detected if not specified)')
        convert_parser.add_argument('--target', help='Target format (auto-detected if not specified)')
        convert_parser.add_argument('--validate', action='store_true', help='Validate conversion')

        # Excel processing commands
        excel_parser = subparsers.add_parser('excel', help='Excel processing commands')
        excel_subparsers = excel_parser.add_subparsers(dest='excel_action', help='Excel actions')

        # Excel extract command
        excel_extract = excel_subparsers.add_parser('extract', help='Extract tables from Excel')
        excel_extract.add_argument('input', help='Input Excel file')
        excel_extract.add_argument('output_dir', help='Output directory for CSV files')

        # Excel validate command
        excel_validate = excel_subparsers.add_parser('validate', help='Validate Excel file')
        excel_validate.add_argument('input', help='Input Excel file')

        # Excel info command
        excel_info = excel_subparsers.add_parser('info', help='Get Excel file information')
        excel_info.add_argument('input', help='Input Excel file')

        # YAML processing commands (existing)
        yaml_parser = subparsers.add_parser('yaml', help='YAML processing commands')
        yaml_subparsers = yaml_parser.add_subparsers(dest='yaml_action', help='YAML actions')

        yaml_process = yaml_subparsers.add_parser('process', help='Process YAML template')
        yaml_process.add_argument('input', help='Input YAML file')
        yaml_process.add_argument('--output', '-o', required=True, help='Output YAML file')
        yaml_process.add_argument('--mode', choices=['rule', 'ai', 'hybrid'],
                                default='hybrid', help='Processing mode')
        yaml_process.add_argument('--mrcf', help='MRCF JSON file path')
        yaml_process.add_argument('--helm', help='Helm charts directory')

        # JSON processing commands (existing)
        json_parser = subparsers.add_parser('json', help='JSON processing commands')
        json_subparsers = json_parser.add_subparsers(dest='json_action', help='JSON actions')

        json_reorder = json_subparsers.add_parser('reorder', help='Reorder JSON Schema')
        json_reorder.add_argument('input', help='Input JSON Schema file')
        json_reorder.add_argument('--output', '-o', required=True, help='Output JSON Schema file')

        return parser

    def initialize_services(self, args) -> bool:
        """Initialize services"""
        try:
            self.orchestrator = UnifiedOrchestratorEngine(args.product, args.version)
            self.conversion_service = FormatConversionService(args.product, args.version)
            self.tracer = TraceHandler(args.product, args.version, "CLI", args.log_level)
            return True
        except Exception as e:
            print(f"Failed to initialize services: {str(e)}")
            return False

    def handle_convert_commands(self, args) -> int:
        """Handle format conversion commands"""
        try:
            success = self.conversion_service.convert_file(
                input_path=args.input,
                output_path=args.output,
                source_format=args.source,
                target_format=args.target
            )

            if success:
                print(f"Successfully converted: {args.input} -> {args.output}")

                # Validate conversion if requested
                if args.validate:
                    valid = self.conversion_service.validate_conversion(args.input, args.output)
                    if valid:
                        print("Conversion validation: PASSED")
                    else:
                        print("Conversion validation: FAILED")
                        return 1

                return 0
            else:
                print(f"Failed to convert: {args.input}")
                return 1

        except Exception as e:
            print(f"Error in conversion: {str(e)}")
            return 1

    def handle_excel_commands(self, args) -> int:
        """Handle Excel processing commands"""
        if args.excel_action == 'extract':
            return self.handle_excel_extract(args)
        elif args.excel_action == 'validate':
            return self.handle_excel_validate(args)
        elif args.excel_action == 'info':
            return self.handle_excel_info(args)
        else:
            print(f"Unknown Excel action: {args.excel_action}")
            return 1

    def handle_excel_extract(self, args) -> int:
        """Handle Excel table extraction"""
        try:
            excel_io = ExcelIOModule(self.tracer)
            results = excel_io.extract_tables(args.input, args.output_dir)

            print(f"Extracted tables from {args.input}:")
            for sheet_name, csv_files in results.items():
                print(f"  Sheet '{sheet_name}': {len(csv_files)} tables")
                for csv_file in csv_files:
                    print(f"    - {csv_file}")

            return 0

        except Exception as e:
            print(f"Error extracting Excel tables: {str(e)}")
            return 1

    def handle_excel_validate(self, args) -> int:
        """Handle Excel validation"""
        try:
            excel_io = ExcelIOModule(self.tracer)
            valid = excel_io.validate_excel(args.input)

            if valid:
                print(f"Excel file is valid: {args.input}")
                return 0
            else:
                print(f"Excel file is invalid: {args.input}")
                return 1

        except Exception as e:
            print(f"Error validating Excel file: {str(e)}")
            return 1

    def handle_excel_info(self, args) -> int:
        """Handle Excel file information"""
        try:
            excel_io = ExcelIOModule(self.tracer)
            sheet_names = excel_io.get_sheet_names(args.input)

            print(f"Excel file information: {args.input}")
            print(f"Number of sheets: {len(sheet_names)}")
            print("Sheet names:")
            for i, name in enumerate(sheet_names, 1):
                print(f"  {i}. {name}")

            return 0

        except Exception as e:
            print(f"Error getting Excel info: {str(e)}")
            return 1

    def handle_yaml_commands(self, args) -> int:
        """Handle YAML processing commands (existing)"""
        if args.yaml_action == 'process':
            return self.handle_yaml_process(args)
        else:
            print(f"Unknown YAML action: {args.yaml_action}")
            return 1

    def handle_yaml_process(self, args) -> int:
        """Handle YAML process command (existing)"""
        try:
            mode_mapping = {
                'rule': ProcessingMode.RULE_BASED,
                'ai': ProcessingMode.AI_BASED,
                'hybrid': ProcessingMode.HYBRID
            }

            mode = mode_mapping.get(args.mode, ProcessingMode.HYBRID)

            success = self.orchestrator.process_yaml_template(
                input_path=args.input,
                output_path=args.output,
                mode=mode,
                mrcf_path=args.mrcf,
                helm_path=args.helm
            )

            if success:
                print(f"Successfully processed YAML: {args.output}")
                return 0
            else:
                print(f"Failed to process YAML: {args.input}")
                return 1

        except Exception as e:
            print(f"Error processing YAML: {str(e)}")
            return 1

    def handle_json_commands(self, args) -> int:
        """Handle JSON processing commands (existing)"""
        if args.json_action == 'reorder':
            return self.handle_json_reorder(args)
        else:
            print(f"Unknown JSON action: {args.json_action}")
            return 1

    def handle_json_reorder(self, args) -> int:
        """Handle JSON reorder command (existing)"""
        try:
            success = self.orchestrator.process_json_schema(
                input_path=args.input,
                output_path=args.output,
                operation='reorder'
            )

            if success:
                print(f"Successfully reordered JSON Schema: {args.output}")
                return 0
            else:
                print(f"Failed to reorder JSON Schema: {args.input}")
                return 1

        except Exception as e:
            print(f"Error reordering JSON Schema: {str(e)}")
            return 1

    def run(self, args=None) -> int:
        """Main CLI entry point"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        if not parsed_args.command:
            parser.print_help()
            return 1

        # Initialize services
        if not self.initialize_services(parsed_args):
            return 1

        # Route to appropriate handler
        try:
            if parsed_args.command == 'convert':
                return self.handle_convert_commands(parsed_args)
            elif parsed_args.command == 'excel':
                return self.handle_excel_commands(parsed_args)
            elif parsed_args.command == 'yaml':
                return self.handle_yaml_commands(parsed_args)
            elif parsed_args.command == 'json':
                return self.handle_json_commands(parsed_args)
            else:
                print(f"Unknown command: {parsed_args.command}")
                return 1

        except KeyboardInterrupt:
            print("\\nOperation cancelled by user")
            return 1
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return 1


def main():
    """Main entry point"""
    cli = EnhancedUnifiedCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())