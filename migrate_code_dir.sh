#!/bin/bash
# Migrate from code/ directory to ai_platform_src/ to avoid stdlib conflict

set -e

echo "This script will rename code/ to ai_platform_src/ to fix the naming conflict"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Rename the directory
mv code ai_platform_src

# Update pyproject.toml
sed -i 's/ai_platform = "code"/ai_platform = "ai_platform_src"/g' pyproject.toml

# Update pdm.build includes
sed -i 's|"code/common"|"ai_platform_src/common"|g' pyproject.toml
sed -i 's|"code/backend"|"ai_platform_src/backend"|g' pyproject.toml

# Reinstall package
pip install -e .

echo "Migration complete! The code/ directory is now ai_platform_src/"
echo "Run: ./run_ml_examples.sh"
