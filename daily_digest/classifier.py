from __future__ import annotations

import re
from collections.abc import Iterator

from daily_digest.models import Article, Category

# 编译后的规则缓存
_rule_cache: dict[str, list[re.Pattern]] | None = None


def build_rules(config: dict) -> dict[str, list[re.Pattern]]:
    """从配置构建编译后的关键词正则。

    config 格式:
        classifier:
          categories:
            AI:
              - keyword1, keyword2        # 逗号 = OR
              - phrase1, phrase2
    """
    rules: dict[str, list[re.Pattern]] = {}
    cats = config.get("classifier", {}).get("categories", {})
    for category, groups in cats.items():
        patterns = []
        for group in groups:
            parts = [k.strip() for k in group.split(",") if k.strip()]
            if not parts:
                continue
            # OR 逻辑：匹配其中任何一个关键词即命中
            pattern = "|".join(re.escape(p) for p in parts)
            patterns.append(re.compile(pattern, re.IGNORECASE))
        if patterns:
            rules[category] = patterns
    return rules


def classify_article(
    article: Article, rules: dict[str, list[re.Pattern]]
) -> tuple[str, float]:
    """对一篇文章分类，返回 (category, confidence)。

    分类逻辑：
    1. 按配置中的分类顺序依次匹配（优先级由前到后递减）
    2. 标题和摘要拼接搜索，任一关键词组命中即归入该类
    3. 返回置信度 = 匹配到的关键词组数 / 该类总词组数
    """
    text = f"{article.title} {article.summary}"
    for category, patterns in rules.items():
        hits = 0
        for p in patterns:
            if p.search(text):
                hits += 1
        if hits > 0:
            confidence = round(hits / len(patterns), 2)
            return category, min(confidence, 0.95)
    return "其他", 0.0


def batch_classify(
    articles: list[Article], config: dict
) -> list[Article]:
    """批量分类，直接修改 article.category。

    策略：
    1. 始终先跑关键词匹配
    2. 关键词返回"其他"时，用 category_hint 兜底
    3. category_hint 也没有时，保持"其他"
    """
    global _rule_cache
    if _rule_cache is None:
        _rule_cache = build_rules(config)

    for article in articles:
        cat, _ = classify_article(article, _rule_cache)
        if cat != "其他":
            article.category = cat
        # 兜底: category_hint（在 fetcher 中已赋给 category）

    return articles
