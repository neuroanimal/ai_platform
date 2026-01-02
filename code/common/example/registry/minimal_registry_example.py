from code.common.core.registry.plugin_registry import PluginRegistry
from code.common.core.interface.plugin_contract import PluginContract


class ExamplePlugin(PluginContract):

    def register(self, registry) -> None:
        registry.register("example.plugin", self)

    def run(self) -> str:
        return "Hello from plugin"


def main() -> None:
    registry = PluginRegistry()

    plugin = ExamplePlugin()
    plugin.register(registry)

    resolved = registry.get("example.plugin")
    print(resolved.run())


if __name__ == "__main__":
    main()
