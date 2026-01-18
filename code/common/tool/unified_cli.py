#!/usr/bin/env python3
"""
AI Platform Unified Processing CLI - Full Integration
Complete command-line interface for all processing functionality
"""
import sys
import os
import argparse
import json
from pathlib import Path

# Add AI Platform to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from code.common.engine.unified_processing_engine import UnifiedProcessingEngine


def create_parser():
    """Create comprehensive argument parser."""
    parser = argparse.ArgumentParser(
        description='AI Platform Unified Processing CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # YAML processing
  %(prog)s yaml input.yaml output.yaml --mrcf config.json --helm charts/ --flavor standard-system
  
  # JSON Schema reordering
  %(prog)s schema input.json output.json --reference ref.json --sort-keywords
  
  # Batch processing
  %(prog)s batch --config batch_config.json
  
  # Auto-detect and process
  %(prog)s auto input_file output_file
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Processing commands')
    
    # YAML processing command
    yaml_parser = subparsers.add_parser('yaml', help='Process YAML templates')
    yaml_parser.add_argument('input', help='Input YAML template file')
    yaml_parser.add_argument('output', help='Output YAML file')
    yaml_parser.add_argument('--mrcf', help='MRCF JSON file path')
    yaml_parser.add_argument('--helm', help='Helm charts directory path')
    yaml_parser.add_argument('--flavor', default='standard-system',
                           choices=['small-system', 'standard-system', 'large-system'],
                           help='System size flavor')
    yaml_parser.add_argument('--no-variants', action='store_true',
                           help='Skip generating rewritten variants')
    yaml_parser.add_argument('--debug', action='store_true', help='Enable debug output')
    yaml_parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    # JSON Schema processing command
    schema_parser = subparsers.add_parser('schema', help='Process JSON Schemas')
    schema_parser.add_argument('input', help='Input JSON Schema file')
    schema_parser.add_argument('output', help='Output JSON Schema file')
    schema_parser.add_argument('--reference', help='Reference JSON/YAML file for ordering')
    schema_parser.add_argument('--no-sort', action='store_true', help='Keep original keyword order')
    schema_parser.add_argument('--merge-leaf', action='store_true', 
                             help='Merge leaf properties from reference')
    schema_parser.add_argument('--validate', action='store_true', help='Validate schema structure')
    schema_parser.add_argument('--info', action='store_true', help='Show schema information')
    
    # Batch processing command
    batch_parser = subparsers.add_parser('batch', help='Batch process multiple files')
    batch_parser.add_argument('--config', required=True, help='Batch configuration JSON file')
    batch_parser.add_argument('--parallel', action='store_true', help='Process files in parallel')
    
    # Auto-detect command
    auto_parser = subparsers.add_parser('auto', help='Auto-detect and process files')
    auto_parser.add_argument('input', help='Input file')
    auto_parser.add_argument('output', help='Output file')
    auto_parser.add_argument('--reference', help='Reference file (for schemas)')
    auto_parser.add_argument('--validate', action='store_true', help='Enable validation')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show engine information')
    info_parser.add_argument('--capabilities', action='store_true', help='Show capabilities')
    info_parser.add_argument('--stats', action='store_true', help='Show processing stats')
    
    return parser


def handle_yaml_command(args, engine):
    """Handle YAML processing command."""
    print(f"Processing YAML template: {args.input}")
    
    config = {}
    if args.debug:
        config['debug'] = True
    if args.verbose:
        config['verbose'] = True
    
    # Update engine config
    engine.yaml_service.config.update(config)
    
    result = engine.process_yaml_template(
        input_path=args.input,
        output_path=args.output,
        mrcf_path=args.mrcf,
        helm_path=args.helm,
        system_size=args.flavor,
        generate_variants=not args.no_variants
    )
    
    if result['success']:
        print(f"✓ {result['message']}")
        print(f"Generated files:")
        for file_path in result['files_generated']:
            print(f"  - {file_path}")
    else:
        print(f"✗ {result['message']}")
        if 'error' in result:
            print(f"Error: {result['error']}")
        return False
    
    return True


def handle_schema_command(args, engine):
    """Handle JSON Schema processing command."""
    print(f"Processing JSON Schema: {args.input}")
    
    result = engine.reorder_json_schema(
        schema_path=args.input,
        output_path=args.output,
        reference_path=args.reference,
        sort_keywords=not args.no_sort,
        merge_leaf_properties=args.merge_leaf
    )
    
    if result['success']:
        print(f"✓ {result['message']}")
        
        if args.validate or args.info:
            # Load and analyze schema
            with open(args.input, 'r') as f:
                schema = json.load(f)
            
            if args.validate:
                validation = engine.schema_service.validate_schema_structure(schema)
                print(f"\nValidation Results:")
                print(f"  Valid: {validation['valid']}")
                if validation['issues']:
                    print(f"  Issues: {len(validation['issues'])}")
                    for issue in validation['issues']:
                        print(f"    - {issue}")
                if validation['recommendations']:
                    print(f"  Recommendations:")
                    for rec in validation['recommendations']:
                        print(f"    - {rec}")
            
            if args.info:
                info = engine.schema_service.get_schema_info(schema)
                print(f"\nSchema Information:")
                print(f"  Type: {info['type']}")
                print(f"  Keywords: {info['keyword_count']}")
                print(f"  Complexity: {info['complexity']}")
                if info['has_properties']:
                    print(f"  Properties: {info['property_count']}")
    else:
        print(f"✗ {result['message']}")
        if 'error' in result:
            print(f"Error: {result['error']}")
        return False
    
    return True


def handle_batch_command(args, engine):
    """Handle batch processing command."""
    print(f"Batch processing from config: {args.config}")
    
    try:
        with open(args.config, 'r') as f:
            batch_config = json.load(f)
        
        files = batch_config.get('files', [])
        options = batch_config.get('options', {})
        
        print(f"Processing {len(files)} files...")
        
        result = engine.batch_process(files, **options)
        
        print(f"✓ {result['message']}")
        print(f"Success rate: {result['successful']}/{result['total']}")
        
        if result['failed'] > 0:
            print(f"Failed files:")
            for res in result['results']:
                if not res.get('success', False):
                    print(f"  - {res.get('file', {}).get('input', 'unknown')}: {res.get('message', 'unknown error')}")
        
        return result['success']
        
    except Exception as e:
        print(f"✗ Batch processing failed: {e}")
        return False


def handle_auto_command(args, engine):
    """Handle auto-detect processing command."""
    print(f"Auto-processing: {args.input} -> {args.output}")
    
    validation_config = {}
    if args.validate:
        validation_config = {
            'validate_yaml': True,
            'validate_schema': True
        }
    
    result = engine.validate_and_process(
        input_path=args.input,
        output_path=args.output,
        validation_config=validation_config,
        reference_path=args.reference
    )
    
    if result['success']:
        print(f"✓ {result['message']}")
        if 'validation' in result:
            validation = result['validation']
            print(f"Validation: {'✓ Valid' if validation['valid'] else '✗ Issues found'}")
    else:
        print(f"✗ {result['message']}")
        if 'error' in result:
            print(f"Error: {result['error']}")
        return False
    
    return True


def handle_info_command(args, engine):
    """Handle info command."""
    if args.capabilities:
        caps = engine.get_capabilities()
        print("Engine Capabilities:")
        print(f"  Name: {caps['name']} v{caps['version']}")
        print(f"  Services:")
        for service_name, service_info in caps['services'].items():
            print(f"    {service_info['name']}:")
            print(f"      Supports: {', '.join(service_info['supports'])}")
            print(f"      Formats: {', '.join(service_info['formats'])}")
    
    if args.stats:
        stats = engine.get_processing_stats()
        print("Processing Statistics:")
        for service_name, service_stats in stats.items():
            print(f"  {service_name}:")
            for key, value in service_stats.items():
                if isinstance(value, dict):
                    print(f"    {key}: {len(value)} items")
                else:
                    print(f"    {key}: {value}")
    
    if not args.capabilities and not args.stats:
        # Show basic info
        caps = engine.get_capabilities()
        print(f"{caps['name']} v{caps['version']}")
        print(f"Available services: {', '.join(caps['services'].keys())}")
        print(f"Unified features: {', '.join(caps['unified_features'])}")
    
    return True


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize engine
    engine = UnifiedProcessingEngine()
    
    # Handle commands
    try:
        if args.command == 'yaml':
            success = handle_yaml_command(args, engine)
        elif args.command == 'schema':
            success = handle_schema_command(args, engine)
        elif args.command == 'batch':
            success = handle_batch_command(args, engine)
        elif args.command == 'auto':
            success = handle_auto_command(args, engine)
        elif args.command == 'info':
            success = handle_info_command(args, engine)
        else:
            print(f"Unknown command: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())