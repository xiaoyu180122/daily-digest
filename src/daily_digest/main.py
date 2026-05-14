"""
每日信息聚合 —— 主编排入口

用法:
    python -m daily_digest.main          # 全流程运行
    python -m daily_digest.main --report  # 只从已有数据生成报告
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import yaml

from daily_digest.classifier import batch_classify
from daily_digest.fetcher_factory import create_fetcher
from daily_digest.reporter import write_report
from daily_digest.storage import get_connection, init_db, insert_articles


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


async def run_pipeline(config: dict) -> int:
    """全流程: 抓取 → 分类 → 存储。返回新文章总数。"""
    conn = get_connection(config.get("storage", {}).get("db_path", "data/digest.db"))
    init_db(conn)

    sources = config.get("sources", [])
    if not sources:
        print("⚠️  配置中没有定义信息源", file=sys.stderr)
        return 0

    total_new = 0
    total_fail = 0

    for src_cfg in sources:
        sid = src_cfg["id"]
        print(f"  ▶ {sid} ({src_cfg.get('name', '')}) ... ", end="", flush=True)

        try:
            fetcher = create_fetcher(src_cfg)
            result = await fetcher.fetch()

            if not result.success:
                print(f"❌ {result.error}")
                total_fail += 1
                continue

            if not result.articles:
                print("∅ (无新内容)")
                continue

            # 分类
            batch_classify(result.articles, config)

            # 存储
            new_count = insert_articles(conn, result.articles)
            total_new += new_count
            print(f"✅ +{new_count}/{len(result.articles)} 条")

        except Exception as e:
            print(f"💥 异常: {e}")
            total_fail += 1

    conn.close()
    print(f"\n📊 汇总: 新增 {total_new} 条，失败 {total_fail} 个源")
    return total_new


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="每日信息聚合工具")
    parser.add_argument(
        "--config", default="config.yaml", help="配置文件路径"
    )
    parser.add_argument(
        "--report", action="store_true", help="仅生成报告（不抓取）"
    )
    parser.add_argument(
        "--output-dir", default="output", help="报告输出目录"
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(str(config_path))

    if not args.report:
        print("🚀 开始每日信息聚合")
        print("=" * 50)
        t0 = time.time()
        await run_pipeline(config)
        elapsed = time.time() - t0
        print(f"⏱  耗时: {elapsed:.1f}s")
        print()

    print("📝 生成报告 ...")
    out = write_report(args.output_dir)
    print(f"✅ 报告已生成: {out}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
