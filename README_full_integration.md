# AI Platform - Full Integration

All-purpose general and broad AI Platform with Traditional and Modern AI, NLP, OCR, ML, DL, LLM, GenAI, AI Agents.

**Now with complete YAML and JSON Schema processing capabilities fully integrated.**

## Overview
Package ai-platform is a modular, extensible AI/DS/ML platform designed for:
- rapid development of AI solutions,
- support for Traditional and Modern AI (including Generative AI),
- maximum architectural rigor with good skeleton prepared,
- technology agnosticism,
- and long-term scalability.

## Principles
- Add-only evolution
- Strong layer boundaries
- Plugin-based extensibility
- Multi-language support

## Fully Integrated Processing Services

### YAML Processing Service (Complete uncomment-00 Integration)
Full merge of uncomment-00 functionality with all original features:

```python
from code.backend.service_layer.yaml_processing.yaml_processing_service import YAMLProcessingService

yaml_service = YAMLProcessingService()
result = yaml_service.process_yaml_template(
    input_path="template.yaml",
    output_path="result.yaml",
    mrcf_path="config.json",
    helm_path="charts/",
    system_size="standard-system",
    generate_variants=True
)
```

**Features:**
- Complete YAML uncommenting with all edge cases
- MRCF integration for parameter resolution
- Helm charts integration
- Multi-flavor support (small/standard/large-system)
- Comprehensive error fixing
- Value substitution with priorities
- Variant generation (Ruamel, PyYAML)
- Full preprocessing and postprocessing pipeline

### JSON Schema Processing Service (Complete jsonschema_reorder Integration)
Full merge of jsonschema_reorder functionality with enhanced features:

```python
from code.backend.service_layer.schema_processing.jsonschema_processing_service import JSONSchemaProcessingService

schema_service = JSONSchemaProcessingService()
result = schema_service.reorder_from_files(
    schema_path="schema.json",
    reference_path="reference.json",
    output_path="reordered.json",
    sort_keywords=True,
    merge_leaf_properties=True
)
```

**Features:**
- Complete JSON Schema reordering
- Reference-based property ordering
- Keyword sorting by JSON Schema standards
- Leaf property merging
- Batch processing capabilities
- Schema validation and analysis
- Complexity calculation
- Support for all JSON Schema keywords

### Unified Processing Engine
Single interface combining both services:

```python
from code.common.engine.unified_processing_engine import UnifiedProcessingEngine

engine = UnifiedProcessingEngine()

# Process YAML
yaml_result = engine.process_yaml_template("template.yaml", "result.yaml")

# Process JSON Schema
schema_result = engine.reorder_json_schema("schema.json", "reordered.json")

# Batch process multiple files
batch_result = engine.batch_process([
    {'type': 'yaml', 'input': 'template.yaml', 'output': 'result.yaml'},
    {'type': 'json', 'input': 'schema.json', 'output': 'reordered.json'}
])
```

### Comprehensive CLI Interface
Complete command-line interface for all functionality:

```bash
# YAML processing with all options
python code/common/tool/unified_cli.py yaml template.yaml result.yaml \
  --mrcf config.json --helm charts/ --flavor standard-system --debug

# JSON Schema processing with validation
python code/common/tool/unified_cli.py schema schema.json reordered.json \
  --reference ref.json --validate --info

# Batch processing
python code/common/tool/unified_cli.py batch --config batch_config.json

# Auto-detect and process
python code/common/tool/unified_cli.py auto input_file output_file --validate
```

## Architecture - Full Integration

```
ai_platform/
├── code/
│   ├── backend/
│   │   └── service_layer/
│   │       ├── yaml_processing/
│   │       │   └── yaml_processing_service.py     # Complete uncomment-00 merge
│   │       └── schema_processing/
│   │           └── jsonschema_processing_service.py # Complete jsonschema_reorder merge
│   ├── common/
│   │   ├── engine/
│   │   │   └── unified_processing_engine.py       # Combined engine
│   │   └── tool/
│   │       └── unified_cli.py                     # Comprehensive CLI
│   └── frontend/
├── test/
│   └── functional/
│       └── integration_test/
│           └── test_full_integration.py           # Complete test suite
└── config/
    └── requirements/
        └── yaml.txt                               # All dependencies
```

## Complete Feature Set

### YAML Processing (All uncomment-00 features)
- ✅ Complete YAML uncommenting pipeline
- ✅ MRCF JSON parameter integration
- ✅ Helm charts value integration
- ✅ Multi-system-size support
- ✅ Priority-based value resolution
- ✅ Comprehensive error fixing
- ✅ Indentation correction
- ✅ Special content handling
- ✅ JSON block processing
- ✅ Variant generation (Ruamel/PyYAML)
- ✅ Full preprocessing/postprocessing
- ✅ Edge case handling
- ✅ Debug and verbose modes

### JSON Schema Processing (All jsonschema_reorder features)
- ✅ Complete schema reordering
- ✅ Reference-based ordering
- ✅ Keyword sorting by standards
- ✅ Leaf property merging
- ✅ Nested schema processing
- ✅ All JSON Schema keywords support
- ✅ Batch processing
- ✅ Schema validation
- ✅ Structure analysis
- ✅ Complexity calculation
- ✅ JSON/YAML reference files
- ✅ Comprehensive error handling

### Unified Features
- ✅ Single engine interface
- ✅ Auto-detection processing
- ✅ Batch processing
- ✅ Validation and analysis
- ✅ Comprehensive CLI
- ✅ Complete test coverage
- ✅ Production-ready error handling

## Installation

Install all dependencies:
```bash
pip install -r config/requirements/yaml.txt
```

## Migration from Original Projects

This is a **complete merge**, not a wrapper:
- **All source code** from uncomment-00 and jsonschema_reorder is integrated
- **All functionality** is preserved and enhanced
- **All edge cases** are handled
- **All configuration options** are available
- **Production-ready** with comprehensive testing

## Benefits of Full Integration

1. **Complete Functionality**: All features from both projects
2. **Enhanced Capabilities**: Additional validation and analysis
3. **Unified Interface**: Single API for all processing needs
4. **Production Ready**: Comprehensive error handling and testing
5. **Platform Native**: Follows AI Platform architecture
6. **Extensible**: Easy to add new processing capabilities
7. **Maintainable**: Clean, modular code structure

## Usage Examples

See `code/common/example/` for comprehensive usage examples and `test/functional/integration_test/` for complete test coverage.

The integration provides immediate, full-featured document processing capabilities within the AI Platform while maintaining all original functionality and adding new unified features.

See [Architecture](doc/arch/ARCHITECTURE.md) and [Dependency Rules](doc/arch/DEPENDENCY_RULES.md) for details.