from __future__ import annotations

import httpx

from daily_digest.fetchers.base import SourceFetcher
from daily_digest.models import Article, FetchResult

HN_BEST_URL = "https://hacker-news.firebaseio.com/v0/beststories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
USER_AGENT = "DailyDigest/0.1"


class HackerNewsApiFetcher(SourceFetcher):
    """通过 HN 官方 Firebase API 获取最佳故事。免费、无限制、免认证。"""

    async def fetch(self) -> FetchResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(HN_BEST_URL)
                resp.raise_for_status()
                ids = resp.json()[:30]
            except Exception as e:
                return FetchResult(
                    source_id=self.source_id,
                    articles=[], success=False, error=str(e),
                )

            articles: list[Article] = []
            for item_id in ids:
                try:
                    item_resp = await client.get(HN_ITEM_URL.format(item_id))
                    item_resp.raise_for_status()
                    item = item_resp.json()
                    if not item or item.get("type") != "story":
                        continue
                except Exception:
                    continue

                title = (item.get("title") or "").strip()
                url = (item.get("url") or
                       f"https://news.ycombinator.com/item?id={item_id}")
                if not title:
                    continue

                score = int(item.get("score", 0))
                hot = 1
                if score > 200:
                    hot = 5
                elif score > 100:
                    hot = 4
                elif score > 50:
                    hot = 3
                elif score > 10:
                    hot = 2

                from datetime import datetime, timezone
                published = datetime.fromtimestamp(
                    int(item.get("time", 0)), tz=timezone.utc
                ) if item.get("time") else None

                text = item.get("text") or ""
                if not text.strip():
                    comments = int(item.get("descendants", 0))
                    text = f"👍 {score} points · 💬 {comments} comments"
                else:
                    text = text[:300]

                articles.append(Article(
                    title=title,
                    url=url,
                    source_id=self.source_id,
                    source_name=self.source_name,
                    summary=text,
                    published_at=published,
                    language=self.language,
                    category=self.config.get("category_hint", "技术"),
                    hot_score=hot,
                ))

            return FetchResult(source_id=self.source_id, articles=articles)
