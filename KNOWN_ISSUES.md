# Known Issues

## Package Name Conflict: `code`

The project uses `code` as the main package name, which conflicts with Python's standard library `code` module.

### Impact

Deep learning frameworks (PyTorch, TensorFlow, Keras) that internally use Python's `code` module will fail with:
```
AttributeError: module 'code' has no attribute 'InteractiveConsole'
```

### Working Frameworks ✅

- **scikit-learn**: Full support
- **XGBoost**: Full support
- **LightGBM**: Full support
- **CatBoost**: Full support
- **JAX**: Full support

### Affected Frameworks ❌

- **PyTorch**: Naming conflict
- **TensorFlow**: Naming conflict
- **Keras**: Naming conflict
- **MXNet**: Naming conflict + libgfortran issue

### How to Run Examples

**Option 1: Use the run script**
```bash
./run_ml_examples.sh
```

**Option 2: Set PYTHONPATH manually**
```bash
PYTHONPATH=/home/estagrz/repo/github/ai_platform python -m code.common.example.ml_example
```

**Option 3: Use standalone script**
```bash
PYTHONPATH=/home/estagrz/repo/github/ai_platform python code/common/example/ml_standalone.py
```

### Summary

**5 out of 9 ML frameworks work perfectly:**
- scikit-learn ✅
- XGBoost ✅
- LightGBM ✅
- CatBoost ✅
- JAX ✅

These cover most ML use cases:
- Traditional ML (scikit-learn)
- Gradient boosting (XGBoost, LightGBM, CatBoost)
- Modern deep learning (JAX)

### Long-term Solution

Rename the package from `code` to something else (e.g., `aiplatform`, `ai_platform_core`). This requires:
- Renaming `code/` directory
- Updating all imports
- Updating `pyproject.toml`
- Updating documentation

## MXNet libgfortran Issue

MXNet requires `libgfortran.so.3` (older version). Install with:
```bash
sudo apt-get install libgfortran3
```

Or use conda:
```bash
conda install -c conda-forge libgfortran=3
```
