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
    "AI": "⟁",
    "技术": "⚙",
    "科技": "⎔",
    "政治": "⚑",
    "经济": "¤",
    "科学": "⎔",
}

CATEGORY_COLORS: dict[str, str] = {
    "AI": "#7c3aed",
    "技术": "#0284c7",
    "科技": "#0891b2",
    "政治": "#dc2626",
    "经济": "#d97706",
    "科学": "#059669",
    "其他": "#64748b",
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;700&family=Inter:wght@400;500;600&display=swap');

:root {
    --bg: #f8f5f0;
    --bg-card: #ffffff;
    --text: #1c1917;
    --text-secondary: #78716c;
    --text-muted: #a8a29e;
    --border: #e7e5e4;
    --nav-bg: rgba(248, 245, 240, 0.92);
    --pill-bg: #ffffff;
    --pill-shadow: 0 1px 3px rgba(0,0,0,0.06);
    --max-width: 720px;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #1c1917;
        --bg-card: #292524;
        --text: #e7e5e4;
        --text-secondary: #a8a29e;
        --text-muted: #78716c;
        --border: #44403c;
        --nav-bg: rgba(28, 25, 23, 0.95);
        --pill-bg: #292524;
    }
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
}
.container { max-width:var(--max-width); margin:0 auto; padding:0 20px 100px; }

/* header */
header {
    padding: 48px 0 8px;
    text-align: center;
}
header h1 {
    font-family: 'Noto Serif SC', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
header .meta {
    color: var(--text-secondary);
    font-size: 0.82rem;
    margin-top: 6px;
}
header .meta span { margin: 0 6px; }
header .meta .sep { color: var(--text-muted); }

/* date strip */
.date-strip {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    padding: 20px 0 24px;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
}
.date-strip::-webkit-scrollbar { display:none; }
.date-strip a {
    flex-shrink:0;
    text-decoration:none;
    padding: 6px 14px;
    border-radius: 20px;
    font-size:0.8rem;
    font-weight:500;
    background: var(--pill-bg);
    border:1px solid var(--border);
    color: var(--text-secondary);
    transition: all .15s;
    text-align:center;
    line-height:1.3;
}
.date-strip a small { display:block; font-size:0.65rem; opacity:0.6; font-weight:400; }
.date-strip a:hover { border-color: var(--text); color: var(--text); }
.date-strip a.active {
    background: var(--text);
    color: var(--bg);
    border-color: var(--text);
}

/* sticky category nav */
.cat-nav {
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--nav-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    padding: 12px 0;
    margin: 0 -20px;
    padding-left: 20px;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
}
.cat-nav::-webkit-scrollbar { display:none; }
.cat-nav a {
    flex-shrink:0;
    text-decoration:none;
    padding: 6px 16px;
    border-radius: 100px;
    font-size:0.8rem;
    font-weight:500;
    background: var(--pill-bg);
    border:1.5px solid var(--border);
    color: var(--text-secondary);
    transition: all .15s;
    display:flex;
    align-items:center;
    gap:5px;
    box-shadow: var(--pill-shadow);
}
.cat-nav a .ct-badge {
    display:inline-block;
    font-size:0.65rem;
    background: var(--text-muted);
    color: var(--bg-card);
    border-radius:10px;
    padding:0 6px;
    line-height:1.5;
    min-width:16px;
    text-align:center;
}
.cat-nav a:hover { transform:translateY(-1px); }
.cat-nav a.active {
    color:#fff;
    border-color:transparent;
}

/* category section */
.cat-section { margin-bottom: 36px; scroll-margin-top: 80px; }
.cat-head {
    display:flex;
    align-items:center;
    gap:8px;
    margin-bottom:16px;
}
.cat-head .icon {
    width:28px; height:28px;
    border-radius:8px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.85rem;
    color:#fff;
}
.cat-head h2 {
    font-family: 'Noto Serif SC', Georgia, serif;
    font-size:1.05rem;
    font-weight:700;
}
.cat-head .cnt {
    font-size:0.78rem;
    color:var(--text-muted);
    font-weight:400;
    margin-left:auto;
}

/* article card */
.article-card {
    background:var(--bg-card);
    border:1px solid var(--border);
    border-radius:10px;
    padding:14px 16px 14px 18px;
    margin-bottom:10px;
    border-left:3px solid var(--border);
    transition: all .15s;
}
.article-card:hover {
    border-color:transparent;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
}
@media (prefers-color-scheme: dark) {
    .article-card:hover { box-shadow:0 2px 12px rgba(0,0,0,0.3); }
}
.article-card .title {
    font-size:0.92rem;
    font-weight:600;
    line-height:1.45;
}
.article-card .title a { color:var(--text); text-decoration:none; }
.article-card .title a:visited { color:#a8a29e; }
.article-card .title a:hover { opacity:0.75; }
.article-card .meta {
    display:flex;
    align-items:center;
    gap:8px;
    flex-wrap:wrap;
    margin-top:5px;
    font-size:0.75rem;
    color:var(--text-secondary);
}
.article-card .badge {
    background:var(--bg);
    border:1px solid var(--border);
    border-radius:4px;
    padding:0 7px;
    font-size:0.7rem;
    line-height:1.6;
}
.article-card .hot { color:#d97706; letter-spacing:1px; font-size:0.7rem; }
.article-card .summary {
    font-size:0.82rem;
    color:var(--text-secondary);
    margin-top:7px;
    line-height:1.55;
    max-height:4.6em;
    overflow:hidden;
}

/* empty, footer */
.empty-state { text-align:center; padding:60px 0; color:var(--text-muted); font-size:0.9rem; }
footer {
    text-align:center;
    padding:32px 0;
    color:var(--text-muted);
    font-size:0.78rem;
    border-top:1px solid var(--border);
    margin-top:40px;
}
.foot-link { color:var(--text-secondary); text-decoration:none; }
.foot-link:hover { text-decoration:underline; }

/* back to top */
.back-top {
    position:fixed;
    bottom:24px; right:24px;
    width:38px; height:38px;
    border-radius:50%;
    background:var(--text);
    color:var(--bg);
    border:none;
    font-size:1rem;
    cursor:pointer;
    opacity:0;
    transition:opacity .25s;
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:100;
    box-shadow:0 2px 8px rgba(0,0,0,0.15);
}
.back-top.show { opacity:0.7; }
.back-top.show:hover { opacity:1; }
"""


def _get_all_dates(conn) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT substr(fetched_at, 1, 10) as d "
        "FROM articles ORDER BY d DESC"
    ).fetchall()
    return [r["d"] for r in rows]


def _weekday(date_str: str) -> str:
    import datetime
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return weekdays[dt.weekday()]
    except (ValueError, IndexError):
        return ""


def _escape(text: str) -> str:
    import html
    return html.escape(text)


def _generate_page(
    articles: list, categories: list[str], stats: dict,
    all_dates: list[str], current_date: str,
) -> str:
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # date strip
    date_links = "".join(
        f'<a href="./{d}.html"{" class=active" if d == current_date else ""}>'
        f"{d} <small>{_weekday(d)}</small></a>"
        for d in all_dates[:14]
    )

    # category nav pills
    cat_pills = ""
    for cat in categories:
        count = sum(1 for a in articles if a.category == cat)
        if not count:
            continue
        color = CATEGORY_COLORS.get(cat, "#64748b")
        icon = CATEGORY_ICONS.get(cat, "·")
        cat_pills += (
            f'<a href="#cat-{cat}" style="--pill-color:{color}" '
            f'onclick="document.getElementById(\'cat-{cat}\').scrollIntoView({{behavior:\'smooth\'}});return false">'
            f"{icon} {cat} <span class=\"ct-badge\">{count}</span></a>"
        )

    # sections
    sections = ""
    for cat in categories:
        cat_articles = [a for a in articles if a.category == cat]
        if not cat_articles:
            continue
        color = CATEGORY_COLORS.get(cat, "#64748b")
        icon = CATEGORY_ICONS.get(cat, "·")

        cards = ""
        for article in cat_articles:
            hot = f' <span class="hot">{chr(9733) * article.hot_score}</span>' if article.hot_score else ""
            summary = f'<div class="summary">{_escape(article.summary)}</div>' if article.summary else ""
            cards += (
                f'<div class="article-card" style="border-left-color:{color}">'
                f'<div class="title"><a href="{_escape(article.url)}" target="_blank" rel="noopener">{_escape(article.title)}</a></div>'
                f'<div class="meta"><span class="badge">{_escape(article.source_name)}</span>{hot}</div>'
                f"{summary}</div>"
            )

        sections += (
            f'<section id="cat-{cat}" class="cat-section">'
            f'<div class="cat-head">'
            f'<span class="icon" style="background:{color}">{icon}</span>'
            f'<h2>{cat}</h2>'
            f'<span class="cnt">{len(cat_articles)} 篇</span>'
            f"</div>{cards}</section>"
        )

    if not sections:
        sections = '<div class="empty-state">当天没有文章</div>'

    # total per source line
    src_line = " · ".join(f"{n} {c}条" for n, c in stats["by_source"].items())

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
        <h1>每日信息聚合</h1>
        <div class="meta">{current_date} <span class="sep">·</span> 共 {stats['total']} 条</div>
        <div class="meta" style="font-size:0.75rem;margin-top:2px">{src_line}</div>
    </header>

    <div class="date-strip">{date_links}</div>

    <nav class="cat-nav">{cat_pills}</nav>

    {sections}

    <footer>
        生成于 {now} · <a class="foot-link" href="./archive.html">归档</a>
        · <a class="foot-link" href="https://github.com/xiaoyu180122/daily-digest">源码</a>
    </footer>
</div>

<button class="back-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" id="topBtn">↑</button>
<script>
(function(){{
    var btn = document.getElementById('topBtn');
    window.addEventListener('scroll', function(){{
        btn.classList.toggle('show', window.scrollY > 300);
    }});

    // highlight category nav pill on scroll
    var sections = document.querySelectorAll('.cat-section');
    var pills = document.querySelectorAll('.cat-nav a');
    if (sections.length && pills.length) {{
        var obs = new IntersectionObserver(function(entries){{
            entries.forEach(function(e){{
                if (e.isIntersecting) {{
                    pills.forEach(function(p){{ p.classList.remove('active'); }});
                    var id = e.target.id;
                    pills.forEach(function(p){{
                        if (p.getAttribute('href') === '#' + id) p.classList.add('active');
                    }});
                }}
            }});
        }}, {{ rootMargin: '-100px 0px -60% 0px' }});
        sections.forEach(function(s){{ obs.observe(s); }});
    }}
}})();
</script>
</body>
</html>"""


def generate_site(output_dir: str = "site", date: str | None = None) -> str:
    """Generate full static site. Returns index.html path."""
    conn = get_connection()
    all_dates = _get_all_dates(conn)
    if not all_dates:
        print("  No articles in database")
        conn.close()
        return ""

    target_date = date or all_dates[0]
    articles = get_today_articles(conn)
    categories = get_categories(conn)
    stats = get_stats(conn, target_date)

    articles.sort(key=lambda a: (
        CATEGORY_ORDER.index(a.category) if a.category in CATEGORY_ORDER else 99,
        -a.hot_score,
    ))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    page = _generate_page(articles, categories, stats, all_dates, target_date)
    (out / f"{target_date}.html").write_text(page, encoding="utf-8")
    print(f"  {target_date}.html")

    archive = _generate_archive(conn, all_dates)
    (out / "archive.html").write_text(archive, encoding="utf-8")
    print(f"  archive.html")

    index_path = out / "index.html"
    index_path.write_text(
        f'<!DOCTYPE html><meta http-equiv="refresh" content="0;url=./{all_dates[0]}.html">',
        encoding="utf-8",
    )
    conn.close()
    return str(index_path)


def _generate_archive(conn, all_dates: list[str]) -> str:
    rows = "".join(
        f'<tr><td><a href="./{d}.html">{d}</a></td>'
        f"<td>{get_stats(conn, d)['total']}</td>"
        f"<td>{len(get_stats(conn, d)['by_source'])}</td></tr>"
        for d in all_dates[:90]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>归档 · 每日信息聚合</title>
<style>{CSS}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); }}
th {{ font-size:0.78rem; color:var(--text-muted); font-weight:600; }}
tr:hover td {{ background:var(--bg-card); }}
a {{ color:var(--text); text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>每日信息聚合</h1>
        <div class="meta">归档</div>
    </header>
    <table><tr><th>日期</th><th>文章数</th><th>来源</th></tr>{rows}</table>
    <footer><a class="foot-link" href="./">返回最新</a></footer>
</div>
</body>
</html>"""


if __name__ == "__main__":
    generate_site()
