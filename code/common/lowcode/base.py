from abc import ABC, abstractmethod
from typing import Any, Dict

class LowCodeAdapter(ABC):
    """Base low-code/no-code platform adapter interface."""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def deploy_workflow(self, workflow: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass
