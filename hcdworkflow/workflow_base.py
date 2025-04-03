from abc import ABC, abstractmethod
from typing import Any, List, Union


class WorkflowBase(ABC):

    @abstractmethod
    def initialize(
        self,
    ) -> None:
        pass

    @abstractmethod
    def run(self, *args) -> Union[List[Any], Any]:
        pass

    @abstractmethod
    def finalize(self) -> None:
        pass

    @abstractmethod
    def get_state(self) -> str:
        pass

    @abstractmethod
    def set_state(self, state: str) -> None:
        pass

    @abstractmethod
    def get_timestamp(self) -> float:
        pass
