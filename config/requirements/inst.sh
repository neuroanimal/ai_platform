pip install pip-tools

pip-compile base.in
pip-compile pandas.in
pip-compile dask.in
pip-compile pyspark.in
pip-compile test.in

pip install -r config/requirements/base.txt
pip install -r config/requirements/dask.txt
pip install -r config/requirements/test.txt
