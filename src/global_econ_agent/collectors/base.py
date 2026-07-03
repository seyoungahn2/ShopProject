from abc import ABC, abstractmethod

from global_econ_agent.models.schemas import Article


class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> list[Article]:
        """수집된 기사 목록 반환."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
