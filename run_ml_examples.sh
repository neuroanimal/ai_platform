#!/bin/bash
# Run ML examples with stdlib code module protection

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR" && pwd )"

# Pre-load stdlib code module to prevent shadowing
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Running ML examples from: $PROJECT_ROOT"
echo ""

# Run with sitecustomize to fix module resolution
python3 -c "import sys; import code as _c; sys.modules['code'] = _c; exec(open('$PROJECT_ROOT/code/common/example/ml_example.py').read())"
