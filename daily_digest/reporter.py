from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from daily_digest.models import Article, CATEGORY_ORDER
from daily_digest.storage import get_connection, get_today_articles, get_categories, get_stats

# 分类对应的 emoji 图标
CATEGORY_ICONS: dict[str, str] = {
    "AI": "🤖",
    "技术": "🖥",
    "科技": "📡",
    "政治": "🌍",
    "经济": "💰",
    "科学": "🔬",
    "其他": "📌",
}

HOT_SYMBOLS = ["", "★", "★★", "★★★", "★★★★", "★★★★★"]


def generate_markdown(
    articles: list[Article],
    categories: list[str],
    stats: dict,
    date: str | None = None,
) -> str:
    """生成完整 Markdown 报告。"""
    day = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# 📰 每日信息聚合 · {day}",
        "",
        f"> 共 {stats['total']} 条 | 来源: {len(stats['by_source'])} 个",
        "",
        "---",
        "",
        "## 📊 概览",
        "",
    ]

    for source, count in stats["by_source"].items():
        bar = "█" * min(count, 20) + "░" * max(0, 20 - min(count, 20))
        lines.append(f"  {source:12s} {bar} {count} 条")
    lines += ["", "---", ""]

    for cat in categories:
        cat_articles = [a for a in articles if a.category == cat]
        if not cat_articles:
            continue

        icon = CATEGORY_ICONS.get(cat, "📌")
        lines.append(f"## {icon} {cat} ({len(cat_articles)} 条)")
        lines.append("")

        for i, article in enumerate(cat_articles, 1):
            hot_str = HOT_SYMBOLS[article.hot_score] if 0 <= article.hot_score <= 5 else ""
            src_tag = f"`{article.source_name}`"
            lines.append(
                f"{i}. [{article.title}]({article.url}) · {src_tag} {hot_str}"
            )
            if article.summary:
                lines.append(f"   > {article.summary}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append(f"*报告生成时间: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
    return "\n".join(lines)


def write_report(
    output_dir: str = "output",
    date: str | None = None,
) -> str:
    """生成报告并写入文件。返回文件路径。"""
    day = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()

    categories = get_categories(conn)
    articles = get_today_articles(conn)
    stats = get_stats(conn, day)

    # 按 CATEGORY_ORDER 排序
    articles.sort(
        key=lambda a: (
            CATEGORY_ORDER.index(a.category) if a.category in CATEGORY_ORDER else 99,
            -a.hot_score,
        )
    )

    md = generate_markdown(articles, categories, stats, day)

    out_path = Path(output_dir) / f"digest-{day}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    conn.close()
    return str(out_path)
