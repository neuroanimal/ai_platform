# AI Platform

All-purpose general and broad AI Platform with Traditional and Modern AI, NLP, OCR, ML, DL, LLM, GenAI, AI Agents.

## Overview

Package ai-platform is a modular, extensible AI/DS/ML platform designed for:

- rapid development of AI solutions,
- support for Traditional AI and Modern AI (including Generative AI),
- maximum architectural rigor with good skeleton prepared,
- technology agnosticism,
- and long-term scalability.

## Principles

- Add-only evolution
- Strong layer boundaries
- Plugin-based extensibility
- Multi-language support

## Integrated Tools

### YAML Processing Tool

Integrated YAML uncommenting functionality for DevOps and configuration management:

```python
from code.common.tool.yaml_uncommenter import YAMLUncommenter

uncommenter = YAMLUncommenter()
success = uncommenter.process(
    input_path="template.yaml",
    output_path="result.yaml",
    system_size="standard-system"
)
```

### JSON Schema Reorder Tool

Integrated JSON Schema reordering functionality for API and data structure management:

```python
from code.common.tool.jsonschema_reorder import JSONSchemaReorder

reorder = JSONSchemaReorder()
result = reorder.reorder(schema, reference_schema)
```

### Engine Interfaces

```python
from code.common.engine.yaml_processing_engine import YAMLProcessingEngine
from code.common.engine.jsonschema_processing_engine import JSONSchemaProcessingEngine

yaml_engine = YAMLProcessingEngine()
schema_engine = JSONSchemaProcessingEngine()

yaml_result = yaml_engine.process_template("template.yaml", "result.yaml")
schema_result = schema_engine.reorder_schema(schema, reference)
```

### CLI Usage

```bash
# YAML processing
python code/common/tool/yaml_cli.py input.yaml output.yaml --flavor standard-system

# JSON Schema reordering
python code/common/tool/jsonschema_cli.py schema.json output.json --reference ref.json
```

## Installation

Install processing dependencies:

```bash
pip install -r config/requirements/yaml.txt
```

## Architecture

The integrated tools follow AI Platform architecture:

- **Tools** (`code/common/tool/`): Direct functionality
- **Engines** (`code/common/engine/`): Higher-level interfaces  
- **Examples** (`code/common/example/`): Usage demonstrations
- **Tests** (`test/functional/integration_test/`): Integration testing

## Integration Benefits

- **Minimal Code**: Essential functionality only
- **Platform Consistency**: Follows AI Platform patterns
- **Extensible**: Easy to add new processing capabilities
- **Testable**: Integrated testing framework
- **Production Ready**: Proven processing logic

## Supported Formats

- **YAML**: Templates, configurations, Kubernetes manifests
- **JSON**: Schemas, APIs, data structures
- **References**: JSON/YAML reference files for ordering

See [Architecture](doc/arch/ARCHITECTURE.md) and [Dependency Rules](doc/arch/DEPENDENCY_RULES.md) for details.
