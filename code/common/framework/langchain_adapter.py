"""LangChain adapter (``langchain-core`` Runnables).

Configuration, one of:

- ``runnable``: any LangChain ``Runnable`` (chain, agent executor, ...);
  ``execute({"input": x})`` calls ``runnable.invoke(x)``;
- ``prompt`` (template string, f-string syntax) and ``llm`` (a platform LLM
  adapter): the adapter builds ``PromptTemplate | <llm call> | StrOutputParser``
  for you. ``input`` is then a dict of template variables (or a string for a
  template with one variable).

``output`` is the chain's result (a string for the built chain).
Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    FrameworkError,
    require_module,
    task_input,
)


class LangChainAdapter(FrameworkBase):
    """Runs a LangChain Runnable."""

    FRAMEWORK = "LangChain"

    def __init__(self):
        super().__init__()
        self.runnable = None

    def _setup(self, config: Dict[str, Any]) -> None:
        if config.get("runnable") is not None:
            self.runnable = config["runnable"]
            return
        if not config.get("prompt") or config.get("llm") is None:
            raise FrameworkError("LangChainAdapter needs 'runnable', or 'prompt' and 'llm'")
        prompts = require_module("langchain_core.prompts", "langchain-core")
        runnables = require_module("langchain_core.runnables", "langchain-core")
        parsers = require_module("langchain_core.output_parsers", "langchain-core")
        llm = config["llm"]

        def call_llm(prompt_value) -> str:
            return llm.chat_completion([{"role": "user", "content": prompt_value.to_string()}]).text

        self.runnable = (prompts.PromptTemplate.from_template(config["prompt"])
                         | runnables.RunnableLambda(call_llm)
                         | parsers.StrOutputParser())

    def _run(self, task: Dict[str, Any]):
        value = task_input(task)
        if isinstance(value, str) and self.config.get("prompt"):
            variables = self.runnable.first.input_variables
            if len(variables) != 1:
                raise FrameworkError(f"input must be a dict of {variables}")
            value = {variables[0]: value}
        result = self.runnable.invoke(value)
        return result, result
