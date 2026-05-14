from __future__ import annotations

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from daily_digest.fetchers.base import SourceFetcher
from daily_digest.models import Article, FetchResult

TRENDING_URL = "https://github.com/trending"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class GitHubTrendingFetcher(SourceFetcher):
    """抓取 GitHub Trending 页面。无需 API key。"""

    async def fetch(self) -> FetchResult:
        try:
            async with httpx.AsyncClient(
                timeout=30.0, headers={"User-Agent": USER_AGENT}
            ) as client:
                resp = await client.get(TRENDING_URL, follow_redirects=True)
                resp.raise_for_status()
        except Exception as e:
            return FetchResult(
                source_id=self.source_id,
                articles=[], success=False, error=str(e),
            )

        soup = BeautifulSoup(resp.text, "lxml")
        articles: list[Article] = []
        now = datetime.now(tz=timezone.utc)

        for repo in soup.select("article.Box-row")[:20]:
            name_h2 = repo.select_one("h2 a")
            if not name_h2:
                continue

            repo_name = name_h2.get("href", "").strip("/")
            full_url = f"https://github.com/{repo_name}"

            desc_el = repo.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            stars = 0
            star_el = repo.select_one(".octicon-star")
            if star_el:
                parent = star_el.find_parent()
                if parent:
                    try:
                        stars = int(parent.get_text(strip=True).replace(",", ""))
                    except ValueError:
                        pass

            lang = repo.select_one("[itemprop='programmingLanguage']")
            lang_str = lang.get_text(strip=True) if lang else ""

            today_stars = 0
            for span in repo.select("span"):
                text = span.get_text(strip=True)
                if "," in text and ("star" in text or "★" in text):
                    try:
                        today_stars = int(
                            text.split(",")[0].replace(" ", "").strip()
                        )
                    except ValueError:
                        pass

            hot = 1
            if today_stars > 500 or stars > 10000:
                hot = 5
            elif today_stars > 200 or stars > 5000:
                hot = 4
            elif today_stars > 50 or stars > 1000:
                hot = 3
            elif today_stars > 10:
                hot = 2

            lang_tag = f" [{lang_str}]" if lang_str else ""

            articles.append(Article(
                title=f"{repo_name}{lang_tag}",
                url=full_url,
                source_id=self.source_id,
                source_name=self.source_name,
                summary=desc[:300],
                published_at=now,
                language=self.language,
                category=self.config.get("category_hint", "技术"),
                hot_score=hot,
            ))

        return FetchResult(source_id=self.source_id, articles=articles)
