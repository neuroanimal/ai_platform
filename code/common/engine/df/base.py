"""
Base abstract class for DataFrame adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, TypeVar, cast

T = TypeVar("T")

class BaseDataFrame(ABC):
    df: Optional[Any]

    def _require_df(self) -> Any:
        df = self.df
        if df is None:
            raise RuntimeError("DataFrame not loaded")
        return df

    @abstractmethod
    def load(self, source: str, **kwargs) -> None:
        """Load data from source (CSV, Parquet, etc.)"""

    @abstractmethod
    def normalize(self) -> None:
        """Normalize data (e.g., handle missing values, convert data types)"""

    @abstractmethod
    def save(self, destination: str, **kwargs) -> None:
        """Save data to destination"""

    @abstractmethod
    def head(self, n: int = 5) -> Any:
        """Return first n rows"""

    @abstractmethod
    def describe(self) -> Any:
        """Return summary statistics"""

    @abstractmethod
    def select(self, columns: List[str]) -> Any:
        """Select specific columns"""

    @abstractmethod
    def filter(self, condition: Any) -> Any:
        """Filter rows based on condition"""
