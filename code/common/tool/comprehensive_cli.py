"""
Comprehensive CLI Interface - Unified command-line interface for all processing capabilities
Integrates YAML processing, JSON Schema processing, and orchestration features
"""
import argparse
import sys
import os
import json
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.engine.unified_orchestrator_engine import UnifiedOrchestratorEngine, ProcessingMode
from common.handler.trace_handler import TraceHandler


class ComprehensiveCLI:
    """Comprehensive CLI for AI Platform processing capabilities"""
    
    def __init__(self):
        self.orchestrator = None
        self.tracer = None
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create comprehensive argument parser"""
        parser = argparse.ArgumentParser(
            description='AI Platform - Comprehensive Processing CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # YAML Processing
  python comprehensive_cli.py yaml process input.yaml --output output.yaml --mode hybrid
  python comprehensive_cli.py yaml process input.yaml --output output.yaml --mrcf config.json --helm charts/
  
  # JSON Schema Processing
  python comprehensive_cli.py json reorder schema.json --output reordered.json
  python comprehensive_cli.py json validate schema.json
  
  # Batch Processing
  python comprehensive_cli.py batch process input_dir/ output_dir/ --pattern "*.yaml" --mode ai
  
  # ML Analysis Workflow
  python comprehensive_cli.py workflow ml-analysis input.yaml output_dir/ --mrcf config.json
            """
        )
        
        # Global arguments
        parser.add_argument('--product', default='AI_Platform', help='Product name')
        parser.add_argument('--version', default='1.0', help='Version')
        parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        parser.add_argument('--config', help='Configuration file path')
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # YAML processing commands
        yaml_parser = subparsers.add_parser('yaml', help='YAML processing commands')
        yaml_subparsers = yaml_parser.add_subparsers(dest='yaml_action', help='YAML actions')
        
        # YAML process command
        yaml_process = yaml_subparsers.add_parser('process', help='Process YAML template')
        yaml_process.add_argument('input', help='Input YAML file')
        yaml_process.add_argument('--output', '-o', required=True, help='Output YAML file')
        yaml_process.add_argument('--mode', choices=['rule', 'ai', 'hybrid', 'ml', 'direct'], 
                                default='hybrid', help='Processing mode')
        yaml_process.add_argument('--mrcf', help='MRCF JSON file path')
        yaml_process.add_argument('--helm', help='Helm charts directory')
        yaml_process.add_argument('--system-size', default='standard-system',
                                choices=['small-system', 'standard-system', 'large-system'],
                                help='System size flavor')
        
        # YAML validate command
        yaml_validate = yaml_subparsers.add_parser('validate', help='Validate YAML syntax')
        yaml_validate.add_argument('input', help='Input YAML file')
        
        # JSON Schema processing commands
        json_parser = subparsers.add_parser('json', help='JSON Schema processing commands')
        json_subparsers = json_parser.add_subparsers(dest='json_action', help='JSON actions')
        
        # JSON reorder command
        json_reorder = json_subparsers.add_parser('reorder', help='Reorder JSON Schema')
        json_reorder.add_argument('input', help='Input JSON Schema file')
        json_reorder.add_argument('--output', '-o', required=True, help='Output JSON Schema file')
        json_reorder.add_argument('--custom-order', help='Custom ordering configuration file')
        
        # JSON validate command
        json_validate = json_subparsers.add_parser('validate', help='Validate JSON Schema')
        json_validate.add_argument('input', help='Input JSON Schema file')
        
        # JSON analyze command
        json_analyze = json_subparsers.add_parser('analyze', help='Analyze JSON Schema complexity')
        json_analyze.add_argument('input', help='Input JSON Schema file')
        json_analyze.add_argument('--output', '-o', help='Output analysis file')
        
        # Batch processing commands
        batch_parser = subparsers.add_parser('batch', help='Batch processing commands')
        batch_subparsers = batch_parser.add_subparsers(dest='batch_action', help='Batch actions')
        
        # Batch process command
        batch_process = batch_subparsers.add_parser('process', help='Batch process files')
        batch_process.add_argument('input_dir', help='Input directory')
        batch_process.add_argument('output_dir', help='Output directory')
        batch_process.add_argument('--pattern', default='*.yaml', help='File pattern to match')
        batch_process.add_argument('--mode', choices=['rule', 'ai', 'hybrid'], 
                                 default='hybrid', help='Processing mode')
        batch_process.add_argument('--mrcf', help='MRCF JSON file path')
        batch_process.add_argument('--helm', help='Helm charts directory')
        
        # Workflow commands
        workflow_parser = subparsers.add_parser('workflow', help='Workflow commands')
        workflow_subparsers = workflow_parser.add_subparsers(dest='workflow_action', help='Workflow actions')
        
        # ML Analysis workflow
        ml_workflow = workflow_subparsers.add_parser('ml-analysis', help='Run ML analysis workflow')
        ml_workflow.add_argument('input', help='Input YAML file')
        ml_workflow.add_argument('output_dir', help='Output directory')
        ml_workflow.add_argument('--mrcf', help='MRCF JSON file path')
        ml_workflow.add_argument('--helm', help='Helm charts directory')
        
        # Auto-detect command
        auto_parser = subparsers.add_parser('auto', help='Auto-detect and process')
        auto_parser.add_argument('input', help='Input file')
        auto_parser.add_argument('--output', '-o', required=True, help='Output file')
        auto_parser.add_argument('--mode', choices=['rule', 'ai', 'hybrid'], 
                               default='hybrid', help='Processing mode')
        
        return parser
    
    def initialize_orchestrator(self, args) -> bool:
        """Initialize orchestrator with configuration"""
        try:
            # Load configuration if provided
            config = {}
            if args.config and os.path.exists(args.config):
                with open(args.config, 'r') as f:
                    config = json.load(f)
            
            # Initialize orchestrator
            self.orchestrator = UnifiedOrchestratorEngine(
                product=args.product,
                version=args.version,
                config=config
            )
            
            # Initialize tracer
            self.tracer = TraceHandler(args.product, args.version, "CLI", args.log_level)
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize orchestrator: {str(e)}")
            return False
    
    def handle_yaml_commands(self, args) -> int:
        """Handle YAML processing commands"""
        if args.yaml_action == 'process':
            return self.handle_yaml_process(args)
        elif args.yaml_action == 'validate':
            return self.handle_yaml_validate(args)
        else:
            print(f"Unknown YAML action: {args.yaml_action}")
            return 1
    
    def handle_yaml_process(self, args) -> int:
        """Handle YAML process command"""
        try:
            # Map mode string to enum
            mode_mapping = {
                'rule': ProcessingMode.RULE_BASED,
                'ai': ProcessingMode.AI_BASED,
                'hybrid': ProcessingMode.HYBRID,
                'ml': ProcessingMode.ML_ANALYSIS,
                'direct': ProcessingMode.DIRECT_PROCESSING
            }
            
            mode = mode_mapping.get(args.mode, ProcessingMode.HYBRID)
            
            success = self.orchestrator.process_yaml_template(
                input_path=args.input,
                output_path=args.output,
                mode=mode,
                mrcf_path=args.mrcf,
                helm_path=args.helm,
                system_size=args.system_size
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
    
    def handle_yaml_validate(self, args) -> int:
        """Handle YAML validate command"""
        try:
            valid = self.orchestrator.yaml_service.validate_yaml_syntax(args.input)
            
            if valid:
                print(f"YAML file is valid: {args.input}")
                return 0
            else:
                print(f"YAML file is invalid: {args.input}")
                return 1
                
        except Exception as e:
            print(f"Error validating YAML: {str(e)}")
            return 1
    
    def handle_json_commands(self, args) -> int:
        """Handle JSON Schema processing commands"""
        if args.json_action == 'reorder':
            return self.handle_json_reorder(args)
        elif args.json_action == 'validate':
            return self.handle_json_validate(args)
        elif args.json_action == 'analyze':
            return self.handle_json_analyze(args)
        else:
            print(f"Unknown JSON action: {args.json_action}")
            return 1
    
    def handle_json_reorder(self, args) -> int:
        """Handle JSON reorder command"""
        try:
            kwargs = {}
            if args.custom_order:
                kwargs['custom_order_file'] = args.custom_order
            
            success = self.orchestrator.process_json_schema(
                input_path=args.input,
                output_path=args.output,
                operation='reorder',
                **kwargs
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
    
    def handle_json_validate(self, args) -> int:
        """Handle JSON validate command"""
        try:
            success = self.orchestrator.process_json_schema(
                input_path=args.input,
                output_path="",  # Not needed for validation
                operation='validate'
            )
            
            if success:
                print(f"JSON Schema is valid: {args.input}")
                return 0
            else:
                print(f"JSON Schema is invalid: {args.input}")
                return 1
                
        except Exception as e:
            print(f"Error validating JSON Schema: {str(e)}")
            return 1
    
    def handle_json_analyze(self, args) -> int:
        """Handle JSON analyze command"""
        try:
            success = self.orchestrator.process_json_schema(
                input_path=args.input,
                output_path=args.output or "",
                operation='analyze'
            )
            
            if success:
                print(f"Successfully analyzed JSON Schema: {args.input}")
                return 0
            else:
                print(f"Failed to analyze JSON Schema: {args.input}")
                return 1
                
        except Exception as e:
            print(f"Error analyzing JSON Schema: {str(e)}")
            return 1
    
    def handle_batch_commands(self, args) -> int:
        """Handle batch processing commands"""
        if args.batch_action == 'process':
            return self.handle_batch_process(args)
        else:
            print(f"Unknown batch action: {args.batch_action}")
            return 1
    
    def handle_batch_process(self, args) -> int:
        """Handle batch process command"""
        try:
            mode_mapping = {
                'rule': ProcessingMode.RULE_BASED,
                'ai': ProcessingMode.AI_BASED,
                'hybrid': ProcessingMode.HYBRID
            }
            
            mode = mode_mapping.get(args.mode, ProcessingMode.HYBRID)
            
            results = self.orchestrator.run_batch_processing(
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                file_pattern=args.pattern,
                mode=mode,
                mrcf_path=args.mrcf,
                helm_path=args.helm
            )
            
            print(f"Batch processing completed:")
            print(f"  Total files: {results['total_files']}")
            print(f"  Successful: {results['successful_files']}")
            print(f"  Failed: {results['failed_files']}")
            
            if results['errors']:
                print("Errors:")
                for error in results['errors']:
                    print(f"  - {error}")
            
            return 0 if results['failed_files'] == 0 else 1
            
        except Exception as e:
            print(f"Error in batch processing: {str(e)}")
            return 1
    
    def handle_workflow_commands(self, args) -> int:
        """Handle workflow commands"""
        if args.workflow_action == 'ml-analysis':
            return self.handle_ml_analysis_workflow(args)
        else:
            print(f"Unknown workflow action: {args.workflow_action}")
            return 1
    
    def handle_ml_analysis_workflow(self, args) -> int:
        """Handle ML analysis workflow"""
        try:
            results = self.orchestrator.run_ml_analysis_workflow(
                input_path=args.input,
                output_dir=args.output_dir,
                mrcf_path=args.mrcf,
                helm_path=args.helm
            )
            
            if results['success']:
                print(f"ML analysis workflow completed successfully")
                print(f"Output directory: {args.output_dir}")
                
                if results['outputs']:
                    print("Generated outputs:")
                    for name, path in results['outputs'].items():
                        if path:
                            print(f"  - {name}: {path}")
                
                return 0
            else:
                print(f"ML analysis workflow failed")
                if 'error' in results:
                    print(f"Error: {results['error']}")
                return 1
                
        except Exception as e:
            print(f"Error in ML analysis workflow: {str(e)}")
            return 1
    
    def handle_auto_command(self, args) -> int:
        """Handle auto-detect command"""
        try:
            mode_mapping = {
                'rule': ProcessingMode.RULE_BASED,
                'ai': ProcessingMode.AI_BASED,
                'hybrid': ProcessingMode.HYBRID
            }
            
            mode = mode_mapping.get(args.mode, ProcessingMode.HYBRID)
            
            success = self.orchestrator.auto_detect_and_process(
                input_path=args.input,
                output_path=args.output,
                mode=mode
            )
            
            if success:
                print(f"Successfully processed file: {args.output}")
                return 0
            else:
                print(f"Failed to process file: {args.input}")
                return 1
                
        except Exception as e:
            print(f"Error in auto processing: {str(e)}")
            return 1
    
    def run(self, args=None) -> int:
        """Main CLI entry point"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        if not parsed_args.command:
            parser.print_help()
            return 1
        
        # Initialize orchestrator
        if not self.initialize_orchestrator(parsed_args):
            return 1
        
        # Route to appropriate handler
        try:
            if parsed_args.command == 'yaml':
                return self.handle_yaml_commands(parsed_args)
            elif parsed_args.command == 'json':
                return self.handle_json_commands(parsed_args)
            elif parsed_args.command == 'batch':
                return self.handle_batch_commands(parsed_args)
            elif parsed_args.command == 'workflow':
                return self.handle_workflow_commands(parsed_args)
            elif parsed_args.command == 'auto':
                return self.handle_auto_command(parsed_args)
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
    cli = ComprehensiveCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())