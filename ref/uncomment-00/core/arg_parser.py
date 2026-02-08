import sys
import json
from config.constants import *


def load_messages():
    """Load messages from JSON configuration file."""
    try:
        with open('config/messages.json', 'r', encoding=ENCODING) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"errors": {}, "usage": {}, "processing": {}}


def wrong_syntax(script_name):
    """Display usage information and exit."""
    messages = load_messages()
    usage = messages.get("usage", {})

    print("\n")
    print(f"{usage.get('header', 'Usage:')}")
    print(f"\tpython3 {script_name} $PATH_TO_INPUT_YAML_TEMPLATE_FILE \\")

    for param in usage.get("parameters", []):
        print(f"              {param} \\")

    print("\n")
    print("Where:")
    descriptions = usage.get("descriptions", {})
    print(f"\t$PATH_TO_INPUT_YAML_TEMPLATE_FILE -- {descriptions.get('yaml_template', 'YAML template file path')}")
    print(f"\t$PATH_TO_INPUT_MRCF_JSON_FILE     -- {descriptions.get('mrcf_json', 'MRCF JSON file path')}")
    print(f"\t$PATH_TO_INPUT_HELM_CHARTS_FOLDER -- {descriptions.get('helm_charts', 'Helm charts folder path')}")
    print(f"\t$SYSTEM_SIZE                      -- {descriptions.get('system_size', 'System size specification')}")
    print(f"\t$PATH_TO_CONFIG_YAML_FILE         -- {descriptions.get('config_yaml', 'Config YAML file path')}")

    sys.exit(1)


def parse_arguments():
    """Parse command line arguments."""
    script = sys.argv[0]

    if len(sys.argv) not in [2, 4, 6, 8, 10]:
        wrong_syntax(script)

    config = {
        'script': script,
        'yaml_template_file': sys.argv[1],
        'mrcf_json_file': None,
        'helm_charts_folder': None,
        'system_size': "standard-system",
        'config_yaml_file': './config.yaml'
    }

    # Parse optional arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--mrcf":
            config['mrcf_json_file'] = sys.argv[i + 1]
        elif sys.argv[i] == "--helm":
            config['helm_charts_folder'] = sys.argv[i + 1]
        elif sys.argv[i] == "--flavor":
            config['system_size'] = sys.argv[i + 1]
        elif sys.argv[i] == "--config":
            config['config_yaml_file'] = sys.argv[i + 1]
        i += 2

    return config


def print_configuration(config):
    """Print the parsed configuration."""
    print("Input used:")
    print()
    print(f"\t$SCRIPT = {config['script']}")
    print(f"\t$PATH_TO_INPUT_YAML_TEMPLATE_FILE = {config['yaml_template_file']}")

    if config['mrcf_json_file']:
        print(f"\t$PATH_TO_INPUT_MRCF_JSON_FILE = {config['mrcf_json_file']}")
    if config['helm_charts_folder']:
        print(f"\t$PATH_TO_INPUT_HELM_CHARTS_FOLDER = {config['helm_charts_folder']}")

    print(f"\t$PATH_TO_CONFIG_YAML_FILE = {config['config_yaml_file']}")
    print()