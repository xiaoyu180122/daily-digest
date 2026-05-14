"""
网站生成器 — 从 SQLite 读取数据，生成 GitHub Pages 静态网站。

用法:
    python -c "from daily_digest.web_gen import generate_site; generate_site()"
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from daily_digest.models import CATEGORY_ORDER
from daily_digest.storage import (
    get_connection,
    get_today_articles,
    get_categories,
    get_stats,
)

CATEGORY_ICONS: dict[str, str] = {
    "AI": "🤖",
    "技术": "🖥️",
    "科技": "📡",
    "政治": "🌍",
    "经济": "💰",
    "科学": "🔬",
    "其他": "📌",
}

CATEGORY_COLORS: dict[str, str] = {
    "AI": "#6366f1",
    "技术": "#0ea5e9",
    "科技": "#8b5cf6",
    "政治": "#ef4444",
    "经济": "#f59e0b",
    "科学": "#10b981",
    "其他": "#6b7280",
}

HOT_STARS = ["", "★", "★★", "★★★", "★★★★", "★★★★★"]

CSS = """
:root {
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #0f172a;
    --text-secondary: #64748b;
    --border: #e2e8f0;
    --hover: #f1f5f9;
    --max-width: 800px;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0f172a;
        --card-bg: #1e293b;
        --text: #f1f5f9;
        --text-secondary: #94a3b8;
        --border: #334155;
        --hover: #1e293b;
    }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 0 16px;
}
.container { max-width: var(--max-width); margin: 0 auto; padding: 24px 0 80px; }

/* header */
header {
    text-align: center;
    padding: 40px 0 24px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
}
header h1 { font-size: 1.5rem; font-weight: 700; }
header .subtitle {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-top: 4px;
}

/* date nav */
.date-nav {
    display: flex;
    gap: 8px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 32px;
}
.date-nav a {
    text-decoration: none;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.875rem;
    background: var(--card-bg);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    transition: all .15s;
}
.date-nav a:hover, .date-nav a.active {
    background: var(--text);
    color: var(--bg);
    border-color: var(--text);
}

/* overview */
.overview {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 40px;
}
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.stat-card .num {
    font-size: 1.5rem;
    font-weight: 700;
    line-height: 1.2;
}
.stat-card .label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-top: 2px;
}

/* category section */
.category-section { margin-bottom: 40px; }
.category-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border);
    margin-bottom: 16px;
}
.category-header h2 { font-size: 1.2rem; font-weight: 600; }
.category-header .count {
    font-size: 0.8rem;
    color: var(--text-secondary);
    font-weight: 400;
}

/* article card */
.article-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
    transition: border-color .15s;
}
.article-card:hover { border-color: var(--text-secondary); }
.article-card .title {
    font-size: 0.95rem;
    font-weight: 600;
    line-height: 1.4;
}
.article-card .title a {
    color: var(--text);
    text-decoration: none;
}
.article-card .title a:hover { text-decoration: underline; }
.article-card .meta {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 6px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.article-card .source-badge {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    background: var(--hover);
    border: 1px solid var(--border);
}
.article-card .summary {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-top: 8px;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.article-card .hot {
    color: #f59e0b;
    letter-spacing: 1px;
}
.empty-state {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
    font-size: 0.9rem;
}

/* footer */
footer {
    text-align: center;
    padding: 24px 0;
    color: var(--text-secondary);
    font-size: 0.8rem;
    border-top: 1px solid var(--border);
    margin-top: 40px;
}
"""


def _get_all_dates(conn) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT substr(fetched_at, 1, 10) as d "
        "FROM articles ORDER BY d DESC"
    ).fetchall()
    return [r["d"] for r in rows]


def _generate_page(
    articles: list,
    categories: list[str],
    stats: dict,
    all_dates: list[str],
    current_date: str,
) -> str:
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    date_links = "".join(
        f'<a href="./{d}.html"{" class=active" if d == current_date else ""}>{d}</a>'
        for d in all_dates[:14]
    )

    stat_cards = "".join(
        f'<div class="stat-card">'
        f'<div class="num">{count}</div>'
        f'<div class="label">{name}</div>'
        f"</div>"
        for name, count in stats["by_source"].items()
    )

    sections = ""
    for cat in categories:
        cat_articles = [a for a in articles if a.category == cat]
        if not cat_articles:
            continue

        icon = CATEGORY_ICONS.get(cat, "📌")
        color = CATEGORY_COLORS.get(cat, "#6b7280")
        cards = ""
        for article in cat_articles:
            hot_str = f' <span class="hot">{HOT_STARS[article.hot_score]}</span>' if article.hot_score else ""
            summary_html = f'<div class="summary">{_escape(article.summary)}</div>' if article.summary else ""
            cards += f"""
            <div class="article-card">
                <div class="title"><a href="{_escape(article.url)}" target="_blank" rel="noopener">{_escape(article.title)}</a></div>
                <div class="meta">
                    <span class="source-badge">{_escape(article.source_name)}</span>
                    {hot_str}
                </div>
                {summary_html}
            </div>"""

        sections += f"""
        <div class="category-section">
            <div class="category-header" style="border-bottom-color:{color}40">
                <span>{icon}</span>
                <h2>{cat}</h2>
                <span class="count">({len(cat_articles)} 条)</span>
            </div>
            {cards}
        </div>"""

    if not sections:
        sections = '<div class="empty-state">当天没有文章</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日信息聚合 · {current_date}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
    <header>
        <h1>📰 每日信息聚合</h1>
        <div class="subtitle">{current_date} · 共 {stats['total']} 条 · {len(stats['by_source'])} 个来源</div>
    </header>

    <div class="date-nav">{date_links}</div>

    <div class="overview">{stat_cards}</div>

    {sections}

    <footer>生成时间: {now} · <a href="https://github.com/xiaoyu180122/daily-digest" style="color:var(--text-secondary)">源码</a></footer>
</div>
</body>
</html>"""


def _escape(text: str) -> str:
    import html
    return html.escape(text)


def generate_site(output_dir: str = "site", date: str | None = None) -> str:
    """生成静态网站到 output_dir。返回 index.html 路径。"""
    conn = get_connection()
    all_dates = _get_all_dates(conn)
    if not all_dates:
        print("⚠️  数据库中没有文章")
        conn.close()
        return ""

    target_date = date or all_dates[0]
    articles = get_today_articles(conn)
    categories = get_categories(conn)
    stats = get_stats(conn, target_date)

    articles.sort(
        key=lambda a: (
            CATEGORY_ORDER.index(a.category) if a.category in CATEGORY_ORDER else 99,
            -a.hot_score,
        )
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 生成日期页面
    page = _generate_page(articles, categories, stats, all_dates, target_date)
    page_path = out / f"{target_date}.html"
    page_path.write_text(page, encoding="utf-8")
    print(f"  ✅ {page_path.name}")

    # 生成归档日历导航页面
    archive = _generate_archive(conn, all_dates)
    archive_path = out / "archive.html"
    archive_path.write_text(archive, encoding="utf-8")
    print(f"  ✅ {archive_path.name}")

    # 生成 index.html → 重定向到最新日期
    index_path = out / "index.html"
    index_path.write_text(
        f'<!DOCTYPE html><meta http-equiv="refresh" '
        f'content="0;url=./{all_dates[0]}.html">',
        encoding="utf-8",
    )
    print(f"  ✅ index.html → {all_dates[0]}.html")

    conn.close()
    return str(index_path)


def _generate_archive(conn, all_dates: list[str]) -> str:
    """生成归档页面，列出所有有文章的日期。"""
    rows = []
    for d in all_dates[:90]:
        stats = get_stats(conn, d)
        rows.append(
            f'<tr><td><a href="./{d}.html">{d}</a></td>'
            f"<td>{stats['total']}</td>"
            f"<td>{len(stats['by_source'])}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日信息聚合 · 归档</title>
<style>{CSS}
table {{ width:100%; border-collapse:collapse; margin-top:16px; }}
th, td {{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); }}
th {{ font-size:0.8rem; color:var(--text-secondary); font-weight:600; }}
tr:hover td {{ background:var(--hover); }}
a {{ color:var(--text); text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>📰 每日信息聚合</h1>
        <div class="subtitle">归档</div>
    </header>
    <table>
        <tr><th>日期</th><th>文章数</th><th>来源数</th></tr>
        {''.join(rows)}
    </table>
    <footer><a href="./">返回最新</a></footer>
</div>
</body>
</html>"""


if __name__ == "__main__":
    generate_site()
