from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Category(str, Enum):
    AI = "AI"
    TECH = "技术"
    TECH_ZH = "科技"   # 36Kr/虎嗅/Solidot 类科技媒体
    POLITICS = "政治"
    ECONOMY = "经济"
    SCIENCE = "科学"
    OTHER = "其他"


CATEGORY_ORDER = [c.value for c in Category]


@dataclass
class Article:
    """一条被聚合的信息。URL 是唯一标识，用于去重。"""

    title: str
    url: str
    source_id: str          # 来源 id，如 hackernews
    source_name: str        # 来源显示名，如 "Hacker News"
    summary: str = ""
    published_at: Optional[datetime] = None
    category: str = "其他"
    language: str = "zh"
    hot_score: int = 0      # 1-5 热度分
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]


@dataclass
class FetchResult:
    """一个源的抓取结果"""

    source_id: str
    articles: list[Article]
    success: bool = True
    error: Optional[str] = None
    article_count: int = 0

    def __post_init__(self):
        self.article_count = len(self.articles)
