from __future__ import annotations

from daily_digest.fetchers.base import SourceFetcher
from daily_digest.fetchers.rss import RssFetcher
from daily_digest.fetchers.hackernews import HackerNewsApiFetcher
from daily_digest.fetchers.github import GitHubTrendingFetcher

_FETCHER_MAP: dict[str, type[SourceFetcher]] = {
    "rss": RssFetcher,
    "hackernews_api": HackerNewsApiFetcher,
    "github_trending": GitHubTrendingFetcher,
}


def create_fetcher(source_config: dict) -> SourceFetcher:
    """根据配置中的 type 创建对应的抓取器实例。"""
    stype = source_config.get("type", "rss")
    cls = _FETCHER_MAP.get(stype)
    if cls is None:
        raise ValueError(f"未知的源类型: {stype}")
    return cls(source_config)
