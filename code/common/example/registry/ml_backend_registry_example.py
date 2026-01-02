from code.common.core.registry.plugin_registry import PluginRegistry


class SklearnBackend:
    def train(self) -> str:
        return "Training with scikit-learn"


class TorchBackend:
    def train(self) -> str:
        return "Training with PyTorch"


def main() -> None:
    ml_registry = PluginRegistry()

    ml_registry.register("sklearn", SklearnBackend())
    ml_registry.register("torch", TorchBackend())

    backend = ml_registry.get("torch")
    print(backend.train())


if __name__ == "__main__":
    main()
