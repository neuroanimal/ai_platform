from ai_platform.common.core.registry.plugin_registry import PluginRegistry


class PandasDataFrameAdapter:
    def name(self) -> str:
        return "pandas"

    def describe(self) -> str:
        return "Pandas DataFrame adapter"


class SparkDataFrameAdapter:
    def name(self) -> str:
        return "spark"

    def describe(self) -> str:
        return "Spark DataFrame adapter"


def main() -> None:
    df_registry = PluginRegistry()

    df_registry.register("pandas", PandasDataFrameAdapter())
    df_registry.register("spark", SparkDataFrameAdapter())

    for key, adapter in df_registry.list().items():
        print(key, "->", adapter.describe())


if __name__ == "__main__":
    main()
