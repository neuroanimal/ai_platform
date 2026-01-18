"""
Adapter for R data.frame via rpy2
Uses Builder pattern for initialization
"""

from .base import BaseDataFrame
from typing import Optional, Any
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri

pandas2ri.activate()

class RDataFrameBuilder:
    """
    Builder for RDataFrame
    Can add configs like local env, options, etc.
    """
    def __init__(self):
        self.options = {}

    def set_option(self, key: str, value):
        self.options[key] = value
        return self

    def build(self):
        rdf = RDataFrame()
        # apply options if any
        for key, value in self.options.items():
            ro.r.options(**{key: value})
        return rdf


class RDataFrame(BaseDataFrame):
    def __init__(self):
        # self.df = None
        self.df: Optional[Any] = None

    def _require_df(self):
        df = self.df
        if df is None:
            raise RuntimeError("DataFrame not loaded")

    def load(self, source: str, **kwargs):
        read_csv = ro.r['read.csv']
        self.df = read_csv(source, **kwargs)

    def normalize(self):
        # TODO
        pass

    def save(self, destination: str, **kwargs):
        write_csv = ro.r['write.csv']
        write_csv(self.df, file=destination, **kwargs)

    def head(self, n: int = 5):
        head = ro.r['head']
        return head(self.df, n=n)

    def describe(self):
        summary = ro.r['summary']
        return summary(self.df)

    def select(self, columns):
        col_str = ','.join(columns)
        return ro.r(f"subset(df, select=c({col_str}))")(df=self.df)

    def filter(self, condition):
        return ro.r(f"subset(df, {condition})")(df=self.df)
