from __future__ import annotations

from abc import ABC, abstractmethod

from daily_digest.models import FetchResult


class SourceFetcher(ABC):
    """所有源抓取器的抽象基类。加一个新源 = 继承这个类 + 在 config.yaml 注册。"""

    def __init__(self, source_config: dict) -> None:
        self.config = source_config
        self.source_id: str = source_config["id"]
        self.source_name: str = source_config["name"]
        self.language: str = source_config.get("language", "zh")

    @abstractmethod
    async def fetch(self) -> FetchResult:
        ...
