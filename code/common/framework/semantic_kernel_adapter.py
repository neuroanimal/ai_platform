"""Semantic Kernel adapter.

Configuration: ``kernel`` (``semantic_kernel.Kernel``) and ``function``
(a ``KernelFunction`` registered on it, or its ``(plugin_name, function_name)``).
``execute({"input": {...}})`` calls ``await kernel.invoke(function, **input)``;
``output`` is ``str(FunctionResult)``.

Not verified against an installed Semantic Kernel here (the package was not
installed when this was written); unit tests drive it with a stand-in
object. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    run_sync,
    task_input,
)


class SemanticKernelAdapter(FrameworkBase):
    """Runs a Semantic Kernel kernel function."""

    FRAMEWORK = "Semantic Kernel"

    def _run(self, task: Dict[str, Any]):
        target = self._needs('kernel', 'a semantic_kernel.Kernel')
        function = self._needs("function", "a KernelFunction or (plugin, name)")
        value = task_input(task)
        arguments = value if isinstance(value, dict) else {"input": value}
        if isinstance(function, (tuple, list)):
            result = run_sync(target.invoke(plugin_name=function[0], function_name=function[1],
                                            **arguments))
        else:
            result = run_sync(target.invoke(function, **arguments))
        return str(result), result
