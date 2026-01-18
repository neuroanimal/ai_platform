# YAML Uncommenting Tool - Refactored Version

This is a modularized and refactored version of the original `uncomment_yaml_template.py` script.

## Structure

```
uncomment-00/
├── config/
│   ├── __init__.py
│   ├── constants.py      # Configuration constants
│   └── messages.json     # User messages and strings
├── core/
│   ├── __init__.py
│   ├── arg_parser.py     # Command line argument parsing
│   ├── path_utils.py     # Path processing utilities
│   ├── value_fixer.py    # Value fixing logic
│   └── yaml_utils.py     # YAML processing utilities
├── config.yaml           # Example configuration file
├── uncomment_yaml_template_refactored.py  # Main refactored script
└── uncomment_yaml_template.py             # Original script
```

## Key Improvements

1. **Modular Structure**: Code split into logical modules
2. **Configuration Management**: Constants and messages externalized
3. **Class-based Design**: Main logic encapsulated in YAMLProcessor class
4. **Simplified Error Handling**: Cleaner error processing
5. **Better Separation of Concerns**: Each module has specific responsibilities

## Usage

Same as original script:

```bash
python3 uncomment_yaml_template_refactored.py input.yaml --mrcf data.json --helm charts/ --flavor standard-system --config config.yaml
```

## Configuration

- `config/constants.py`: Adjust processing constants
- `config/messages.json`: Customize user messages
- `config.yaml`: Set value resolution priorities

## Next Steps

This refactored version is ready to be integrated into the AI Platform as a module, following the incremental approach you mentioned.