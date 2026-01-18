"""
Example usage of DataFrame adapters with flag selection
"""

from importlib import import_module
import os.path


def import_class(full_class_path: str):
    """
    Import class by full dotted path.
    Example: code.common.engine.df.pandas_adapter.PandasDataFrame
    """
    module_path, class_name = full_class_path.rsplit(".", 1)
    try:
        module = import_module(module_path)
        return getattr(module, class_name)
    except ImportError:
        pass
    try:
        exec(f"import {full_class_path}")
        return True
    except ImportError:
        print(f"Importing {full_class_path} failed!")
        return False


def detect_available_adapters():
    # Auto detection of available backends
    available_backends = []
    try:
        import pandas
        available_backends.append("Pandas")
    except ImportError:
        pass
    try:
        import dask
        available_backends.append("Dask")
    except ImportError:
        pass
    try:
        import pyspark
        available_backends.append("PySpark")
    except ImportError:
        pass
    try:
        import rpy2
        available_backends.append("R")
    except ImportError:
        pass
    try:
        import julia
        available_backends.append("Julia")
    except ImportError:
        pass
    if not available_backends:
        raise RuntimeError("No DataFrame backend available!")
    return available_backends


def main():
    # Check file to read to not lose time if not available
    input_data_file_path = "data/sample.csv"
    if not os.path.exists(input_data_file_path):
        print(f"File {input_data_file_path} does not exist")
        exit(1)
    elif not os.path.isfile(input_data_file_path):
        print(f"Path {input_data_file_path} is not pointing to a file")
        exit(2)

    # Select wanted backends: 'Pandas', 'Dask', 'PySpark', 'R', 'Julia'
    wanted_backends = ['Pandas', 'Dask', 'PySpark', 'R', 'Julia']
    wanted_usage = ['constructor', 'builder']
    print(f"Wanted usages: {wanted_usage}")
    print(f"Wanted adapters: {wanted_backends}")

    available_backends = detect_available_adapters()
    print(f"Available adapters: {available_backends}")

    for wanted_backend in wanted_backends:
        # backend = 'dask'  # change to 'pandas','pyspark','r','julia'
        backend = wanted_backend.lower()  # .capitalize()
        for wanted_usage in wanted_usage:
            if wanted_backend in available_backends:
                """
                if backend == 'pandas':
                    from code.common.engine.df.pandas_adapter import PandasDataFrame, PandasDataFrameBuilder
                    df = PandasDataFrame()
                    df = PandasDataFrameBuilder().build()
                elif backend == 'dask':
                    from code.common.engine.df.dask_adapter import DaskDataFrame, DaskDataFrameBuilder
                    df = DaskDataFrame()
                    df = DaskDataFrameBuilder().build()
                    df = DaskDataFrameBuilder().set_scheduler("threads").build()
                elif backend == 'pyspark':
                    from code.common.engine.df.pyspark_adapter import PySparkDataFrame, PySparkDataFrameBuilder
                    # SparkSession tworzony tutaj:
                    # ### spark = SparkSession.builder.appName("DFExample").getOrCreate()
                    # ### df = PySparkDataFrame(spark)
                    # SparkSession tworzony wewnątrz adaptera:
                    df = PySparkDataFrame()
                    df = PySparkDataFrameBuilder().build()
                elif backend == 'r':
                    from code.common.engine.df.r_adapter import RDataFrame, RDataFrameBuilder
                    df = RDataFrame()
                    df = RDataFrameBuilder().build()
                elif backend == 'julia':
                    from code.common.engine.df.julia_adapter import JuliaDataFrame, JuliaDataFrameBuilder
                    df = JuliaDataFrame()
                    df = JuliaDataFrameBuilder().build()
                else:
                    raise ValueError(f"Unknown backend {backend}")
                """
                df = None
                mod_prefix = f"code.common.engine.df.{backend}_adapter."
                df_class_name = f"{wanted_backend}DataFrame"
                if wanted_usage == 'constructor':
                    df_class_path = f"{mod_prefix}{df_class_name}"
                    df_constructor_call = f"{df_class_name}()"
                    ClassHandle = import_class(df_class_path)
                    if ClassHandle:
                        if isinstance(ClassHandle, bool):
                            df = eval(df_constructor_call)
                        else:
                            df = ClassHandle()
                elif wanted_usage == 'builder':
                    df_class_name = f"{df_class_name}Builder"
                    df_class_path = f"{mod_prefix}{df_class_name}"
                    df_constructor_call = f"{df_class_name}()"
                    ClassHandle = import_class(df_class_path)
                    if ClassHandle:
                        if isinstance(ClassHandle, bool):
                            df = eval(df_constructor_call).build()
                        else:
                            df = ClassHandle().build()
                else:
                    raise ValueError(f"Unknown usage {wanted_usage}")
                if not df:
                    # raise ValueError(f"Could not instantiate {backend} DataFrame")
                    print(f"Could not instantiate {backend} DataFrame")
                else:
                    df.load(input_data_file_path)
                    df.normalize()
                    print(f"\nHEAD:\n", df.head())
                    print(f"\nDESCRIBE:\n", df.describe())
                    # Example of select and filter
                    print(f"\nSELECT columns ['col1', 'col2']:\n", df.select(['col1', 'col2']))
                    # print(f"FILTER rows 'col1 > 10':\n", df.filter("col1 > 10"))
                    print(f"\nFILTER rows '.1 in col1':\n", df.filter("col1.str.contains('.1')"))  #  col1 > 10


if __name__ == "__main__":
    main()
