"""
Adapter for PySpark DataFrame
Uses Builder pattern to encapsulate SparkSession creation.
"""

from .base import BaseDataFrame
from typing import Optional, Any
from pyspark.sql import SparkSession, DataFrame as SparkDF

class PySparkDataFrameBuilder:
    """
    Builder for SparkSession
    """
    def __init__(self):
        self.app_name = "AIPlatformApp"
        self.master = "local[*]"
        self.configs = {}

    def set_app_name(self, name: str):
        self.app_name = name
        return self

    def set_master(self, master: str):
        self.master = master
        return self

    def set_config(self, key: str, value: str):
        self.configs[key] = value
        return self

    def build_session(self) -> SparkSession:
        builder = SparkSession.builder.appName(self.app_name).master(self.master)
        for key, value in self.configs.items():
            builder = builder.config(key, value)
        spark = builder.getOrCreate()
        return spark

    def build(self) -> 'PySparkDataFrame':
        spark = self.build_session()
        return PySparkDataFrame(spark)


class PySparkDataFrame(BaseDataFrame):
    """
    Adapter for PySpark DataFrame
    """

    def __init__(self, spark: SparkSession = None):
        """
        If spark is None, create default session using Builder
        """
        if spark is None:
            self.spark = PySparkDataFrameBuilder().build_session()
            self.spark = PySparkDataFrameBuilder().build().spark
        else:
            self.spark = spark
        # self.df: SparkDF = None
        self.df: Optional[Any] = None

    def _require_df(self):
        df = self.df
        if df is None:
            raise RuntimeError("DataFrame not loaded")

    def load(self, source: str, **kwargs):
        """Load CSV file into Spark DataFrame"""
        self.df = self.spark.read.csv(source, header=True, inferSchema=True, **kwargs)

    def normalize(self) -> None:
        self._require_df()
        self.df.columns = [
            c.strip().strip('"').strip("'")
            for c in self.df.columns
        ]

    def save(self, destination: str, **kwargs):
        """Save Spark DataFrame to CSV"""
        self.df.write.csv(destination, header=True, **kwargs)

    def head(self, n: int = 5):
        """Return first n rows"""
        return self.df.show(n)

    def describe(self):
        """Return summary statistics"""
        return self.df.describe().show()

    def select(self, columns):
        """Select columns"""
        return self.df.select(*columns)

    def filter(self, condition):
        """Filter rows by condition"""
        return self.df.filter(condition)
