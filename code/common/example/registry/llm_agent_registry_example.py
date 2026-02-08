from ai_platform.common.core.registry.plugin_registry import PluginRegistry


class OpenAILLM:
    def generate(self, prompt: str) -> str:
        return f"OpenAI response to: {prompt}"


class LangGraphAgent:
    def run(self, task: str) -> str:
        return f"LangGraph agent executing: {task}"


def main() -> None:
    llm_registry = PluginRegistry()
    agent_registry = PluginRegistry()

    llm_registry.register("openai", OpenAILLM())
    agent_registry.register("langgraph", LangGraphAgent())

    llm = llm_registry.get("openai")
    agent = agent_registry.get("langgraph")

    print(llm.generate("Hello"))
    print(agent.run("Data analysis"))


if __name__ == "__main__":
    main()
