from __future__ import annotations

from datetime import datetime

from src.config import OUTPUT_DIR, ensure_dirs, load_config, load_seen, save_seen
from src.deepseek import summarize
from src.domestic import domestic_sources_text
from src.feishu import send_text_report
from src.pubmed import search_topics
from src.rank import select_items


def main() -> None:
    ensure_dirs()
    config = load_config()
    seen = load_seen()

    primary_days = int(config.get("lookback_days_primary", 10))
    fallback_days = int(config.get("lookback_days_fallback", 180))
    max_items = int(config.get("max_items", 12))
    topics = config["topics"]

    articles = search_topics(topics, primary_days)
    items = select_items(articles, seen, max_items)
    mode = f"recent {primary_days} days"

    if not items:
        articles = search_topics(topics, fallback_days)
        items = select_items(articles, seen, max_items)
        mode = f"unseen high-value items from recent {fallback_days} days"

    today = datetime.now().strftime("%Y-%m-%d")
    title = f"ENT Head and Neck Guideline Radar | {today}"
    domestic_appendix = domestic_sources_text("耳鼻咽喉头颈外科 指南 共识")

    if items:
        report = summarize(items)
        report = f"检索模式：{mode}\n纳入条目数：{len(items)}\n\n{report}\n\n{domestic_appendix}"
        for item in items:
            seen.add(item.id)
    else:
        report = (
            "本期未检索到新的或未推送过的高价值条目。\n\n"
            "建议下期继续按既定主题监测；如近期有特定专题，可临时增加关键词。\n\n"
            + domestic_appendix
        )

    output_path = OUTPUT_DIR / f"ent_radar_{today}.md"
    output_path.write_text(f"# {title}\n\n{report}\n", encoding="utf-8")
    save_seen(seen)
    send_text_report(title, report)


if __name__ == "__main__":
    main()
