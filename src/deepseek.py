from __future__ import annotations

import json
import os
import urllib.request

from src.pubmed import Article


DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def build_prompt(items: list[Article]) -> str:
    records = []
    for idx, item in enumerate(items, start=1):
        records.append(
            {
                "序号": idx,
                "主题": item.topic,
                "标题": item.title,
                "作者": item.authors,
                "期刊": item.journal,
                "日期": item.pubdate,
                "PMID": item.pmid,
                "DOI": item.doi,
                "链接": item.url,
                "类型": item.pubtypes,
                "摘要": item.abstract[:2500],
            }
        )
    return (
        "你是耳鼻咽喉头颈外科临床文献秘书。请把以下新文献/指南转述成中文详细报告，"
        "要求面向忙碌临床医生，容易阅读，但不要夸大证据。\n\n"
        "输出结构：\n"
        "1. 本期一句话结论\n"
        "2. 本期最值得看的 3-5 条\n"
        "3. 按主题分组逐条说明：原文链接、PMID/DOI、研究/指南类型、核心内容、可能改变的临床决策、是否建议精读\n"
        "4. 证据限制与需要进一步确认的地方\n"
        "5. 可转化为患者科普/短视频的选题\n\n"
        "注意：只能基于给定标题、摘要和元数据总结；没有摘要时要明确说信息有限。"
        "不要编造指南全文内容，不要编造数据。\n\n"
        f"文献列表 JSON：\n{json.dumps(records, ensure_ascii=False, indent=2)}"
    )


def summarize(items: list[Article]) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY")
    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [
            {
                "role": "system",
                "content": "你擅长医学文献解读。请保持严谨、清楚、中文易读，保留原文链接和证据限制。",
            },
            {"role": "user", "content": build_prompt(items)},
        ],
        "temperature": 0.2,
        "max_tokens": 6000,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()
