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
