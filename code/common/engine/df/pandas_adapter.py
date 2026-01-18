from .base import BaseDataFrame
from typing import Optional, Any
import pandas as pd

class PandasDataFrameBuilder:
    """
    Builder for PandasDataFrame
    """
    def __init__(self):
        self.options = {}

    def set_option(self, key: str, value):
        self.options[key] = value
        return self

    def build(self):
        df = PandasDataFrame()
        for key, value in self.options.items():
            setattr(df, key, value)
        return df

class PandasDataFrame(BaseDataFrame):
    def __init__(self):
        # self.df = None
        self.df: Optional[Any] = None

    def _require_df(self):
        df = self.df
        if df is None:
            raise RuntimeError("DataFrame not loaded")

    def load(self, source: str, **kwargs):
        self.df = pd.read_csv(source, **kwargs)

    def normalize(self) -> None:
        self._require_df()
        self.df.columns = [
            c.strip().strip('"').strip("'")
            for c in self.df.columns
        ]

    def save(self, destination: str, **kwargs):
        self.df.to_csv(destination, index=False, **kwargs)

    def head(self, n: int = 5):
        return self.df.head(n)

    def describe(self):
        return self.df.describe()

    def select(self, columns):
        return self.df[columns]

    def filter(self, condition):
        return self.df.query(condition)
