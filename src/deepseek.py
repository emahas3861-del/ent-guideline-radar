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
                "摘要": item.abstract[:2200],
            }
        )
    return (
        "你是耳鼻咽喉头颈外科临床文献秘书。请把以下新文献或指南转述成中文详细报告。"
        "直接进入报告，不要写‘好的、收到’等客套话。报告面向忙碌临床医生，要求清楚、紧凑、严谨，不夸大证据。\n\n"
        "输出结构：\n"
        "# 耳鼻咽喉头颈外科文献雷达\n"
        "## 本期结论\n用2-4句话概括真正可能影响临床或科普表达的变化。\n"
        "## 最值得看的更新\n列3-5条，每条包含：主题、原文链接、为什么重要。\n"
        "## 分主题详读\n按主题分组。每篇文献使用固定字段：原文、类型、核心发现、临床影响、建议。"
        "每个字段尽量1-2句，保留关键数字和限制；不要为了短而省略会影响理解的适用人群、风险或证据限制。\n"
        "## 需要谨慎解读\n只列最关键限制，不要逐篇写长段。\n"
        "## 可转化为科普/短视频\n给3-5个选题，每个选题一句话说明基于哪篇文献。\n\n"
        "筛选原则：如果某条与耳鼻咽喉头颈外科关系弱，请放到‘低相关/仅供浏览’或不重点展开。"
        "只能基于给定标题、摘要和元数据总结；没有摘要时要明确说信息有限。不要编造指南全文内容，不要编造数据。\n\n"
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
                "content": "你擅长医学文献解读。请保持严谨、清楚、中文易读，保留原文链接和证据限制。输出应像正式周报，不要客套。",
            },
            {"role": "user", "content": build_prompt(items)},
        ],
        "temperature": 0.2,
        "max_tokens": 4500,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()
