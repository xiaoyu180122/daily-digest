from __future__ import annotations

import calendar
from datetime import datetime, timezone

import feedparser
import httpx

from daily_digest.fetchers.base import SourceFetcher
from daily_digest.models import Article, FetchResult

USER_AGENT = (
    "Mozilla/5.0 (compatible; DailyDigest/0.1; "
    "+https://github.com/your/daily-digest)"
)


class RssFetcher(SourceFetcher):
    """通用 RSS 源抓取器。覆盖大多数博客和新闻站。"""

    async def fetch(self) -> FetchResult:
        url = self.config["url"]
        headers = {"User-Agent": USER_AGENT}
        if extra := self.config.get("headers"):
            headers.update(extra)
        try:
            async with httpx.AsyncClient(
                timeout=30.0, headers=headers
            ) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
        except Exception as e:
            return FetchResult(
                source_id=self.source_id,
                articles=[],
                success=False,
                error=str(e),
            )

        feed = feedparser.parse(resp.text)
        articles: list[Article] = []
        for entry in feed.entries[:self.config.get("max_items", 30)]:
            link = entry.get("link", "").strip()
            if not link:
                continue

            published = None
            if pub := entry.get("published_parsed"):
                published = datetime.fromtimestamp(
                    calendar.timegm(pub), tz=timezone.utc
                )

            summary = ""
            if s := entry.get("summary", ""):
                summary = _strip_html(s)[:300]
            elif s := entry.get("description", ""):
                summary = _strip_html(s)[:300]

            articles.append(Article(
                title=_strip_html(entry.get("title", "")).strip(),
                url=link,
                source_id=self.source_id,
                source_name=self.source_name,
                summary=summary,
                published_at=published,
                language=self.language,
                category=self.config.get("category_hint", "其他"),
                hot_score=_infer_hot_score(entry),
            ))

        return FetchResult(source_id=self.source_id, articles=articles)


def _strip_html(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    return text.strip()


def _infer_hot_score(entry: dict) -> int:
    """根据 RSS 条目中的评论数/点赞数估算热度 1-5。"""
    score = 1
    if comments := entry.get("comments"):
        score += 1
    if slash := entry.get("slash_comments", {}).get("commented"):
        try:
            c = int(slash)
            if c > 50:
                score += 2
            elif c > 10:
                score += 1
        except (ValueError, TypeError):
            pass
    return min(score, 5)
