# Configuration constants
DEBUG = False
VERBOSE = False
FORCE_REWRITING = True
STOP_ON_RUAMEL_ERROR = False
STOP_ON_PYYAML_ERROR = False
MAX_NUM_OF_ERRORS_TO_BE_FIXED = 2000

# File extensions and patterns
YAML_EXTENSION = '.yaml'
UNCOMMENTED_SUFFIX = '_uncommented'

# System size mappings
SYSTEM_SIZE_MAPPING = {
    "small-system": "default_small_system_profile",
    "standard-system": "default_standard_system_profile",
    "large-system": "default_large_system_profile",
}

# Default priorities
DEFAULT_PRIORITIES = [
    "MRCF.recommended_value",
    "MRCF.default_per_flavor",
    "MRCF.default",
    "YAML.default_per_flavor",
    "HELM.default",
    "MRCF.example",
]

# YAML processing constants
DELIMITER = "/"
TAB_SIZE = 2
CLEAN_CHARS = "\r\n"

# File encoding
ENCODING = "UTF-8"