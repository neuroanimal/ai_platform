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

## New Features

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

### Engine Interface

```python
from code.common.engine.yaml_processing_engine import YAMLProcessingEngine

engine = YAMLProcessingEngine()
result = engine.process_template(
    input_path="template.yaml",
    output_path="result.yaml",
    mrcf_path="config.json",
    helm_path="charts/",
    system_size="large-system"
)
```

### CLI Usage

```bash
python code/common/tool/yaml_cli.py input.yaml output.yaml --flavor standard-system --helm charts/
```

## Installation

Install YAML processing dependencies:

```bash
pip install -r config/requirements/yaml.txt
```

## Architecture

The YAML processing functionality follows AI Platform architecture:

- **Tools** (`code/common/tool/`): Direct functionality
- **Engines** (`code/common/engine/`): Higher-level interfaces  
- **Examples** (`code/common/example/`): Usage demonstrations
- **Tests** (`test/functional/integration_test/`): Integration testing

## Integration Benefits

- **Minimal Code**: Essential functionality only
- **Platform Consistency**: Follows AI Platform patterns
- **Extensible**: Easy to add new processing capabilities
- **Testable**: Integrated testing framework
- **Production Ready**: Proven uncommenting logic

See [Architecture](doc/arch/ARCHITECTURE.md) and [Dependency Rules](doc/arch/DEPENDENCY_RULES.md) for details.
