from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from daily_digest.models import Article


def _get_db_path() -> str:
    """默认数据库路径，可通过环境变量覆盖。"""
    import os
    return os.getenv("DIGEST_DB_PATH", "data/digest.db")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    p = db_path or _get_db_path()
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            url         TEXT NOT NULL,
            source_id   TEXT NOT NULL,
            source_name TEXT NOT NULL,
            summary     TEXT DEFAULT '',
            category    TEXT DEFAULT '其他',
            language    TEXT DEFAULT 'zh',
            hot_score   INTEGER DEFAULT 0,
            published_at TEXT,
            fetched_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_category ON articles(category);
        CREATE INDEX IF NOT EXISTS idx_fetched ON articles(fetched_at);
        CREATE INDEX IF NOT EXISTS idx_source ON articles(source_id);
    """)
    conn.commit()


def insert_articles(
    conn: sqlite3.Connection, articles: Sequence[Article]
) -> int:
    """批量插入，URL 重复的自动跳过 (去重)。返回实际插入条数。"""
    count = 0
    for a in articles:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO articles
                   (id, title, url, source_id, source_name, summary,
                    category, language, hot_score, published_at, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a.id,
                    a.title,
                    a.url,
                    a.source_id,
                    a.source_name,
                    a.summary,
                    a.category,
                    a.language,
                    a.hot_score,
                    a.published_at.isoformat() if a.published_at else None,
                    a.fetched_at.isoformat(),
                ),
            )
            if conn.total_changes > count:
                count += 1
        except Exception:
            continue
    conn.commit()
    return count


def get_today_articles(
    conn: sqlite3.Connection,
    category: str | None = None,
    limit: int = 200,
) -> list[Article]:
    """获取当日文章，按热度降序排列。可选择分类筛选。"""
    from datetime import datetime, timezone, timedelta

    today_start = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    tomorrow = (
        datetime.now(tz=timezone.utc) + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    if category:
        rows = conn.execute(
            """SELECT * FROM articles
               WHERE fetched_at >= ? AND fetched_at < ?
               AND category = ?
               ORDER BY hot_score DESC, published_at DESC
               LIMIT ?""",
            (today_start, tomorrow, category, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM articles
               WHERE fetched_at >= ? AND fetched_at < ?
               ORDER BY hot_score DESC, published_at DESC
               LIMIT ?""",
            (today_start, tomorrow, limit),
        ).fetchall()
    return [_row_to_article(r) for r in rows]


def get_categories(conn: sqlite3.Connection) -> list[str]:
    """获取当日所有非空分类，按固定顺序排列。"""
    from datetime import datetime, timezone, timedelta

    today_start = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    tomorrow = (
        datetime.now(tz=timezone.utc) + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    rows = conn.execute(
        """SELECT category, COUNT(*) as cnt FROM articles
           WHERE fetched_at >= ? AND fetched_at < ?
           GROUP BY category ORDER BY cnt DESC""",
        (today_start, tomorrow),
    ).fetchall()

    from daily_digest.models import CATEGORY_ORDER
    cats = {r["category"] for r in rows}
    return [c for c in CATEGORY_ORDER if c in cats]


def get_stats(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """获取每日统计。"""
    from datetime import datetime, timezone, timedelta

    day = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    tomorrow = (
        datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    total = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE fetched_at >= ? AND fetched_at < ?",
        (day, tomorrow),
    ).fetchone()[0]

    by_source = conn.execute(
        """SELECT source_name, COUNT(*) as cnt FROM articles
           WHERE fetched_at >= ? AND fetched_at < ?
           GROUP BY source_name ORDER BY cnt DESC""",
        (day, tomorrow),
    ).fetchall()

    return {"total": total, "by_source": {r["source_name"]: r["cnt"] for r in by_source}}


def _row_to_article(row: sqlite3.Row) -> Article:
    from datetime import datetime

    return Article(
        title=row["title"],
        url=row["url"],
        source_id=row["source_id"],
        source_name=row["source_name"],
        summary=row["summary"],
        category=row["category"],
        language=row["language"],
        hot_score=row["hot_score"],
        published_at=(
            datetime.fromisoformat(row["published_at"])
            if row["published_at"] else None
        ),
    )
