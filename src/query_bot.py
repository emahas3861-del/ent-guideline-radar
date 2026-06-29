from __future__ import annotations

import re

from src.deepseek import summarize
from src.pubmed import Article, fetch_article_details, search_pmids
from src.rank import score_article

ENT_CONTEXT = """
otolaryngology OR "head and neck" OR rhinology OR otology OR neurotology OR laryngology
OR thyroid OR "salivary gland" OR "head and neck cancer" OR "chronic rhinosinusitis"
OR "sudden hearing loss" OR "sleep apnea" OR "neck mass" OR pediatric otolaryngology
OR "skull base" OR "facial plastic surgery" OR parotidectomy OR thyroidectomy OR tympanoplasty
"""


def answer_query(text: str) -> str:
    query = normalize_query(text)
    if not query:
        return help_text()

    articles = find_articles(query)
    if not articles:
        return (
            "没有检索到明确匹配的 PubMed 结果。\n\n"
            "你可以换一种方式发送：\n"
            "- PMID 40844370\n"
            "- DOI 10.xxxx/xxxxx\n"
            "- 查 最近 突发性耳聋 指南\n"
            "- 查 鼻息肉 生物制剂 最新综述\n"
        )

    selected = sorted(articles, key=score_article, reverse=True)[:5]
    return summarize_for_chat(query, articles, selected)


def normalize_query(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"<at[^>]*>.*?</at>", "", text).strip()
    text = re.sub(r"^(查|帮我查|查询|找|搜索|总结|summarize|summary)\s*", "", text, flags=re.I)
    return text.strip()


def find_articles(query: str) -> list[Article]:
    pmid_match = re.search(r"\bPMID[:：\s]*(\d{6,10})\b", query, flags=re.I) or re.fullmatch(r"\d{7,10}", query.strip())
    if pmid_match:
        pmid = pmid_match.group(1) if pmid_match.lastindex else pmid_match.group(0)
        return fetch_article_details([pmid], {pmid: "即时查询"})

    doi_match = re.search(r"10\.\d{4,9}/[^\s，,；;]+", query, flags=re.I)
    if doi_match:
        doi = doi_match.group(0).rstrip(".。")
        pmids = search_pmids(f'"{doi}"[AID]', lookback_days=3650, retmax=5)
        return fetch_article_details(pmids, {pmid: "即时查询" for pmid in pmids})

    pubmed_query = build_pubmed_query(query)
    pmids = search_pmids(pubmed_query, lookback_days=3650, retmax=15)
    return fetch_article_details(pmids, {pmid: "即时查询" for pmid in pmids})


def build_pubmed_query(query: str) -> str:
    terms = query.replace("，", " ").replace(",", " ").strip()
    low = terms.lower()
    in_scope_terms = [
        "ent", "otolaryngology", "耳鼻", "头颈", "甲状腺", "鼻", "耳", "喉",
        "颅底", "腮腺", "面整", "睡眠", "眩晕", "听力",
    ]
    if any(word in low for word in in_scope_terms):
        base = terms
    else:
        base = f"({terms}) AND ({ENT_CONTEXT})"
    if any(word in low for word in ["guideline", "指南", "共识", "consensus"]):
        return f"({base}) AND (guideline OR consensus OR practice guideline OR clinical practice guideline)"
    return base


def summarize_for_chat(query: str, all_articles: list[Article], selected: list[Article]) -> str:
    report = summarize(selected)
    refs = []
    for item in selected:
        full_text = f"https://pmc.ncbi.nlm.nih.gov/articles/{item.pmcid}/" if item.pmcid else "未发现 PMC 开放全文链接"
        refs.append(
            f"- {item.title}\n"
            f"  PubMed: {item.url}\n"
            f"  DOI: {item.doi or '无'}\n"
            f"  PMC全文: {full_text}"
        )
    return (
        f"即时查询：{query}\n"
        f"检索到 {len(all_articles)} 条，优先总结前 {len(selected)} 条。\n\n"
        f"{report}\n\n"
        "原文与全文线索：\n" + "\n".join(refs)
    )


def help_text() -> str:
    return (
        "可以这样问我：\n"
        "- PMID 40844370\n"
        "- DOI 10.1177/10507256251363120\n"
        "- 查 最近 突发性耳聋 指南\n"
        "- 查 鼻息肉 生物制剂 最新综述\n"
        "- 查 头颈鳞癌 免疫治疗 指南\n\n"
        "说明：我会优先检索 PubMed 和开放全文线索；付费全文不会绕过权限。"
    )