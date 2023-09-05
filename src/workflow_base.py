from abc import ABC, abstractmethod
from typing import Any, List, Union

class WorkflowBase(ABC):

    @abstractmethod
    def initialize(self, ) -> None:
        ...

    @abstractmethod
    def run(self, *args) -> Union[List[Any], Any]:
        ...

    @abstractmethod
    def finalize(self) -> None:
        ...

    @abstractmethod
    def get_state(self) -> str:
        ...

    @abstractmethod
    def set_state(self, state: str) -> None:
        ...

    @abstractmethod
    def get_timestamp(self) -> float:
        ...