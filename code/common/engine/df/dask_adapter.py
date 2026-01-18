"""
Adapter for Dask DataFrame
Uses Builder pattern for potential configuration (future extensions)
"""

from .base import BaseDataFrame
from typing import Optional, Any
import dask.dataframe as dd

class DaskDataFrameBuilder:
    """
    Builder for DaskDataFrame
    Currently minimal, but can add configs like scheduler, chunksize, etc.
    """
    def __init__(self):
        self.scheduler = "threads"  # default
        self.chunksize = None

    def set_scheduler(self, scheduler: str):
        self.scheduler = scheduler
        return self

    def set_chunksize(self, chunksize: int):
        self.chunksize = chunksize
        return self

    def build(self):
        return DaskDataFrame(self.scheduler, self.chunksize)


class DaskDataFrame(BaseDataFrame):
    def __init__(self, scheduler="threads", chunksize=None):
        # self.df = None
        self.df: Optional[Any] = None
        self.scheduler = scheduler
        self.chunksize = chunksize

    def _require_df(self):
        df = self.df
        if df is None:
            raise RuntimeError("DataFrame not loaded")

    def load(self, source: str, **kwargs):
        self.df = dd.read_csv(source, blocksize=self.chunksize, **kwargs)

    def normalize(self) -> None:
        self._require_df()
        self.df.columns = [
            c.strip().strip('"').strip("'")
            for c in self.df.columns
        ]

    def save(self, destination: str, **kwargs):
        self.df.to_csv(destination, single_file=True, index=False, **kwargs)

    def head(self, n: int = 5):
        return self.df.head(n)

    def describe(self):
        return self.df.describe().compute()

    def select(self, columns):
        return self.df[columns]

    def filter(self, condition):
        return self.df.query(condition)
