"""
Architecture rule:
After load() + normalize(), DataFrame adapters must expose
clean column names usable by select().
"""

from code.common.engine.df.pandas_adapter import PandasDataFrame
import tempfile
import os


def _create_dirty_csv(path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            '"col1", "col2", "col3"\n'
            '"v1", "v2", "v3"\n'
        )


def main():
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "dirty.csv")
        _create_dirty_csv(csv_path)

        df = PandasDataFrame()
        df.load(csv_path)
        df.normalize()

        try:
            df.select(["col1", "col2"])
        except Exception as exc:
            raise AssertionError(
                "Architecture rule violated: "
                "select() must work on normalized column names"
            ) from exc

    print("OK: DataFrame normalization architecture rule satisfied")


if __name__ == "__main__":
    main()
