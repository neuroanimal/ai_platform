"""
Adapter for Julia DataFrame via PyJulia
Uses Builder pattern for initialization
"""

from .base import BaseDataFrame
from typing import Optional, Any
from julia import Main
from julia import DataFrames as df

class JuliaDataFrameBuilder:
    """
    Builder for JuliaDataFrame
    Can extend with options like file encodings, parsing options, etc.
    """
    def __init__(self):
        self.options = {}

    def set_option(self, key: str, value):
        self.options[key] = value
        return self

    def build(self):
        jdf = JuliaDataFrame()
        # Apply options here if needed
        return jdf


class JuliaDataFrame(BaseDataFrame):
    def __init__(self):
        # self.df = None
        self.df: Optional[Any] = None

    def _require_df(self):
        df = self.df
        if df is None:
            raise RuntimeError("DataFrame not loaded")

    def load(self, source: str, **kwargs):
        self.df = Main.eval(f'readcsv("{source}")')

    def normalize(self):
        # TODO
        self._require_df()
        pass

    def save(self, destination: str, **kwargs):
        Main.eval(f'writecsv("{destination}", df)')

    def head(self, n: int = 5):
        return Main.eval(f'first(df, {n})')

    def describe(self):
        return Main.eval('describe(df)')

    def select(self, columns):
        col_str = ','.join([f'"{c}"' for c in columns])
        return Main.eval(f'select(df, [{col_str}])')

    def filter(self, condition):
        return Main.eval(f'filter(row -> {condition}, df)')
