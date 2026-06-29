from __future__ import annotations

import re

from src.deepseek import summarize
from src.domestic import domestic_sources_text
from src.pubmed import Article, fetch_article_details, search_pmids
from src.rank import score_article

ENT_CONTEXT = """
otolaryngology OR "head and neck" OR rhinology OR otology OR neurotology OR laryngology
OR thyroid OR "salivary gland" OR "head and neck cancer" OR "chronic rhinosinusitis"
OR "sudden hearing loss" OR "sleep apnea" OR "neck mass" OR pediatric otolaryngology
OR "skull base" OR "facial plastic surgery" OR parotidectomy OR thyroidectomy OR tympanoplasty
"""

TOPIC_MAPPINGS = [
    (
        ["过敏性鼻炎", "变应性鼻炎", "allergic rhinitis", "hay fever"],
        '("allergic rhinitis"[Title/Abstract] OR "rhinitis, allergic"[MeSH Terms] OR "hay fever"[Title/Abstract])',
        ["allergic rhinitis", "rhinitis, allergic", "hay fever"],
    ),
    (
        ["鼻炎", "rhinitis"],
        '(rhinitis[Title/Abstract] OR rhinitis[MeSH Terms])',
        ["rhinitis"],
    ),
    (
        ["慢性鼻窦炎", "鼻窦炎", "鼻息肉", "chronic rhinosinusitis", "nasal polyps"],
        '("chronic rhinosinusitis"[Title/Abstract] OR "rhinosinusitis"[MeSH Terms] OR "nasal polyps"[Title/Abstract] OR "nasal polyps"[MeSH Terms])',
        ["chronic rhinosinusitis", "rhinosinusitis", "nasal polyp", "nasal polyps"],
    ),
    (
        ["突发性耳聋", "突聋", "sudden hearing loss", "sudden sensorineural hearing loss"],
        '("sudden sensorineural hearing loss"[Title/Abstract] OR "hearing loss, sudden"[MeSH Terms])',
        ["sudden sensorineural hearing loss", "sudden hearing loss"],
    ),
    (
        ["眩晕", "梅尼埃", "耳石", "bppv", "meniere", "vertigo"],
        '(vertigo[Title/Abstract] OR vertigo[MeSH Terms] OR "Meniere disease"[Title/Abstract] OR BPPV[Title/Abstract])',
        ["vertigo", "meniere", "bppv", "benign paroxysmal positional vertigo"],
    ),
    (
        ["头颈鳞癌", "头颈癌", "head and neck cancer", "hnscc"],
        '("head and neck cancer"[Title/Abstract] OR "head and neck squamous cell carcinoma"[Title/Abstract] OR HNSCC[Title/Abstract])',
        ["head and neck cancer", "head and neck squamous", "hnscc"],
    ),
    (
        ["甲状腺", "thyroid"],
        '(thyroid[Title/Abstract] OR thyroid[MeSH Terms])',
        ["thyroid"],
    ),
]

GUIDELINE_FILTER = """(
    guideline[Publication Type] OR practice guideline[Publication Type]
    OR guideline[Title] OR guidelines[Title]
    OR consensus[Title] OR guideline*[Title/Abstract] OR consensus[Title/Abstract]
)"""


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
            "- 查 过敏性鼻炎 指南\n"
            "- 查 鼻息肉 生物制剂 最新综述\n\n"
            + domestic_sources_text(query)
        )

    selected = sorted(articles, key=score_article, reverse=True)[:5]
    return summarize_for_chat(query, articles, selected)


def normalize_query(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"<at[^>]*>.*?</at>", "", text).strip()
    text = re.sub(r"@_user_\d+", "", text).strip()
    text = re.sub(r"^@[\w\-\u4e00-\u9fff]+\s*", "", text).strip()
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
    pmids = search_pmids(pubmed_query, lookback_days=3650, retmax=20)
    articles = fetch_article_details(pmids, {pmid: "即时查询" for pmid in pmids})
    focused = filter_by_query_focus(query, articles)
    return focused or articles


def build_pubmed_query(query: str) -> str:
    terms = query.replace("，", " ").replace(",", " ").strip()
    low = terms.lower()
    mapped = mapped_pubmed_terms(terms)
    if mapped:
        base = mapped
    elif query_mentions_ent_scope(low):
        base = terms
    else:
        base = f"({terms}) AND ({ENT_CONTEXT})"
    if any(word in low for word in ["guideline", "指南", "共识", "consensus"]):
        return f"({base}) AND {GUIDELINE_FILTER}"
    return base


def mapped_pubmed_terms(query: str) -> str:
    low = query.lower()
    matched = []
    for triggers, pubmed_terms, _focus_terms in TOPIC_MAPPINGS:
        if any(trigger.lower() in low for trigger in triggers):
            matched.append(pubmed_terms)
    return " AND ".join(matched)


def query_focus_terms(query: str) -> list[str]:
    low = query.lower()
    terms: list[str] = []
    for triggers, _pubmed_terms, focus_terms in TOPIC_MAPPINGS:
        if any(trigger.lower() in low for trigger in triggers):
            terms.extend(focus_terms)
    return terms


def filter_by_query_focus(query: str, articles: list[Article]) -> list[Article]:
    focus_terms = query_focus_terms(query)
    if not focus_terms:
        return articles
    matched = []
    for article in articles:
        haystack = f"{article.title} {article.abstract}".lower()
        if any(term in haystack for term in focus_terms):
            matched.append(article)
    return matched


def query_mentions_ent_scope(low: str) -> bool:
    in_scope_terms = [
        "ent", "otolaryngology", "rhinology", "otology", "laryngology", "allergic rhinitis",
        "耳鼻", "头颈", "甲状腺", "鼻", "耳", "喉", "颅底", "腮腺", "面整", "睡眠", "眩晕", "听力",
    ]
    return any(word in low for word in in_scope_terms)


def summarize_for_chat(query: str, all_articles: list[Article], selected: list[Article]) -> str:
    report = summarize(selected)
    refs = []
    for item in selected:
        full_text = pmc_text(item)
        refs.append(
            f"- {item.title}\n"
            f"  PubMed: {item.url}\n"
            f"  DOI: {item.doi or '无'}\n"
            f"  PMC线索: {full_text}"
        )
    return (
        f"即时查询：{query}\n"
        f"检索到 {len(all_articles)} 条，优先总结前 {len(selected)} 条。\n\n"
        f"{report}\n\n"
        "原文与全文线索：\n" + "\n".join(refs)
        + "\n\n" + domestic_sources_text(query)
    )


def pmc_text(item: Article) -> str:
    if not item.pmcid:
        return "未发现 PMC 线索"
    link = f"https://pmc.ncbi.nlm.nih.gov/articles/{item.pmcid}/"
    if item.pmc_release:
        return f"{link}（PMC release: {item.pmc_release}；若暂不可访问，说明尚未开放）"
    return link


def help_text() -> str:
    return (
        "可以这样问我：\n"
        "- PMID 40844370\n"
        "- DOI 10.1177/10507256251363120\n"
        "- 查 最近 突发性耳聋 指南\n"
        "- 查 过敏性鼻炎 指南\n"
        "- 查 鼻息肉 生物制剂 最新综述\n"
        "- 查 头颈鳞癌 免疫治疗 指南\n\n"
        "说明：我会优先检索 PubMed、PMC 线索和国内权威检索入口；付费全文不会绕过权限。"
    )
