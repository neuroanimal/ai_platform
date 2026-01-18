# Uncomment Project - Integrated Version

This project now integrates both the ML-based approach and the proven uncomment-00 functionality.

## Architecture

```
uncomment/
├── common/                    # Shared utilities
├── engines/
│   ├── ai_engine/            # ML-based structure and template models
│   ├── io_engine/            # Data input/output modules
│   ├── validation_engine/    # Validation components
│   ├── yaml_processor/       # Integrated uncomment-00 functionality
│   │   └── yaml_processor_engine.py
│   ├── orchestrator_engine.py      # Original ML orchestrator
│   └── orchestrator_engine_v2.py   # Enhanced orchestrator with integration
├── data/                     # Test data
├── uncomment_cli.py         # Command-line interface
├── test_integration.py      # Integration tests
└── README.md
```

## Processing Modes

### 1. ML Mode (Original)
Uses machine learning approach with structure and template models:
```python
orchestrator.run_uncomment_process()
```

### 2. Direct Mode (uncomment-00)
Uses proven rule-based approach from uncomment-00:
```python
orchestrator.run_direct_yaml_process(mrcf_path, helm_path, system_size)
```

### 3. Hybrid Mode (Best of Both)
Combines ML analysis with direct processing:
```python
orchestrator.run_hybrid_process(mrcf_path, helm_path, system_size)
```

## Usage

### Command Line Interface
```bash
# Direct processing (recommended for production)
python uncomment_cli.py input.yaml --mode direct --output result.yaml --helm charts/ --flavor standard-system

# Hybrid processing
python uncomment_cli.py input.yaml --mode hybrid --output result.yaml --mrcf data.json --helm charts/

# ML processing
python uncomment_cli.py input.yaml --mode ml --output result.yaml
```

### Programmatic Usage
```python
from engines.orchestrator_engine_v2 import OrchestratorEngine

orchestrator = OrchestratorEngine("PRODUCT", "1.0", {})

# Use direct processing for reliable results
success = orchestrator.run_direct_yaml_process(
    mrcf_path="config.json",
    helm_path="charts/",
    system_size="standard-system"
)
```

## Key Features

- **Proven Reliability**: Direct mode uses battle-tested uncomment-00 logic
- **ML Enhancement**: ML mode provides intelligent analysis capabilities  
- **Flexible Integration**: Hybrid mode combines both approaches
- **Edge Case Handling**: Integrated solution handles more edge cases
- **Modular Design**: Easy to extend and maintain

## Integration Benefits

1. **Immediate Production Use**: Direct mode works reliably now
2. **Future ML Enhancement**: ML components ready for improvement
3. **Gradual Migration**: Can transition from direct to hybrid to ML
4. **Reduced Risk**: Fallback options available
5. **Unified Interface**: Single API for all processing modes

## Next Steps

1. Test with your specific YAML templates
2. Add new edge cases to yaml_processor_engine.py
3. Enhance ML models based on direct processing insights
4. Integrate into AI Platform when ready

The integration provides a solid foundation that works today while enabling future ML enhancements.