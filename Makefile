req:
	cd config/requirements && \
	pip install pip-tools && \
	pip-compile base.in

	cd config/requirements && \
	pip-compile pandas.in && \
	pip-compile dask.in && \
	pip-compile pyspark.in && \
	pip-compile test.in

	cd config/requirements && \
	pip-compile r.in && \
	pip-compile julia.in

	pip install -r config/requirements/base.txt && \
	pip install -r config/requirements/dask.txt && \
	pip install -r config/requirements/test.txt

	pip install -r config/requirements/r.txt
	pip install -r config/requirements/julia.txt

.PHONY: install install-all install-llm install-ml install-rag install-viz install-dev install-js test clean system-deps

# Install system dependencies (Linux/WSL only)
system-deps:
	sudo apt-get update
	sudo apt-get install -y libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev gfortran

# Install JavaScript dependencies
install-js:
	cd config/requirements && yarn install

# Install core only
install:
	pip install -e .

# Install everything (includes PyTorch/TensorFlow)
install-all: system-deps install-js
	export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 && pip install --prefer-binary -e ".[all]"
	pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
	pip install tensorflow jax[cpu] mxnet

# Install LLM components
install-llm: system-deps
	export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 && pip install --prefer-binary -e ".[llm]"

# Install ML components (includes PyTorch/TensorFlow)
install-ml: system-deps
	export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 && pip install --prefer-binary -e ".[ml]"
	pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
	pip install tensorflow jax[cpu] mxnet

# Install RAG components
install-rag: system-deps
	export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 && pip install -e ".[rag,vectordb]"

# Install visualization components
install-viz: system-deps
	export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 && pip install --prefer-binary -e ".[viz]"

# Install development dependencies
install-dev: system-deps
	export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 && pip install --prefer-binary -e ".[all]"
	pip install pytest pytest-cov ruff black isort

# Run tests
test:
	pytest test/

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
