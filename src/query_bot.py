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
        ["鼻出血", "鼻衄", "epistaxis"],
        '(epistaxis[Title/Abstract] OR epistaxis[MeSH Terms] OR "nosebleed"[Title/Abstract] OR "nose bleeding"[Title/Abstract])',
        ["epistaxis", "nosebleed", "nose bleeding"],
    ),
    (
        ["osa", "阻塞性睡眠呼吸暂停", "睡眠呼吸暂停", "鼾症", "打鼾", "sleep apnea", "snoring"],
        '("obstructive sleep apnea"[Title/Abstract] OR "sleep apnea syndromes"[MeSH Terms] OR "OSA"[Title/Abstract] OR "sleep disordered breathing"[Title/Abstract] OR snoring[Title/Abstract])',
        ["obstructive sleep apnea", "sleep apnea", "sleep disordered breathing", "snoring"],
    ),
    (
        ["耳鸣", "tinnitus"],
        '(tinnitus[Title/Abstract] OR tinnitus[MeSH Terms])',
        ["tinnitus"],
    ),
    (
        ["中耳炎", "分泌性中耳炎", "化脓性中耳炎", "otitis media"],
        '("otitis media"[Title/Abstract] OR "otitis media"[MeSH Terms] OR "otitis media with effusion"[Title/Abstract] OR "chronic suppurative otitis media"[Title/Abstract])',
        ["otitis media", "middle ear infection"],
    ),
    (
        ["喉癌", "喉鳞癌", "laryngeal cancer", "larynx cancer"],
        '("laryngeal cancer"[Title/Abstract] OR "laryngeal neoplasms"[MeSH Terms] OR "larynx cancer"[Title/Abstract] OR "laryngeal squamous cell carcinoma"[Title/Abstract])',
        ["laryngeal cancer", "laryngeal neoplasms", "larynx cancer", "laryngeal squamous"],
    ),
    (
        ["涎腺肿瘤", "唾液腺肿瘤", "腮腺肿瘤", "颌下腺肿瘤", "salivary gland tumor", "parotid tumor"],
        '("salivary gland neoplasms"[MeSH Terms] OR "salivary gland tumor"[Title/Abstract] OR "salivary gland neoplasm"[Title/Abstract] OR "parotid neoplasm"[Title/Abstract] OR "parotid tumor"[Title/Abstract])',
        ["salivary gland neoplasm", "salivary gland tumor", "parotid neoplasm", "parotid tumor"],
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

TERM_TRANSLATIONS = [
    ("鼻出血", '"epistaxis"[Title/Abstract] OR epistaxis[MeSH Terms]'),
    ("鼻衄", '"epistaxis"[Title/Abstract] OR epistaxis[MeSH Terms]'),
    ("阻塞性睡眠呼吸暂停", '"obstructive sleep apnea"[Title/Abstract] OR "sleep apnea syndromes"[MeSH Terms]'),
    ("睡眠呼吸暂停", '"sleep apnea"[Title/Abstract] OR "sleep apnea syndromes"[MeSH Terms]'),
    ("鼾症", 'snoring[Title/Abstract] OR snoring[MeSH Terms]'),
    ("打鼾", 'snoring[Title/Abstract] OR snoring[MeSH Terms]'),
    ("耳鸣", 'tinnitus[Title/Abstract] OR tinnitus[MeSH Terms]'),
    ("分泌性中耳炎", '"otitis media with effusion"[Title/Abstract] OR "otitis media with effusion"[MeSH Terms]'),
    ("化脓性中耳炎", '"chronic suppurative otitis media"[Title/Abstract]'),
    ("中耳炎", '"otitis media"[Title/Abstract] OR "otitis media"[MeSH Terms]'),
    ("喉癌", '"laryngeal cancer"[Title/Abstract] OR "laryngeal neoplasms"[MeSH Terms]'),
    ("喉鳞癌", '"laryngeal squamous cell carcinoma"[Title/Abstract]'),
    ("声带白斑", '"vocal cord leukoplakia"[Title/Abstract] OR "vocal fold leukoplakia"[Title/Abstract]'),
    ("声带息肉", '"vocal cord polyp"[Title/Abstract] OR "vocal fold polyp"[Title/Abstract]'),
    ("声嘶", 'dysphonia[Title/Abstract] OR hoarseness[Title/Abstract]'),
    ("嗓音", 'voice[Title/Abstract] OR dysphonia[Title/Abstract]'),
    ("吞咽困难", 'dysphagia[Title/Abstract] OR dysphagia[MeSH Terms]'),
    ("扁桃体", 'tonsil[Title/Abstract] OR tonsillectomy[Title/Abstract]'),
    ("腺样体", 'adenoid[Title/Abstract] OR adenoidectomy[Title/Abstract]'),
    ("涎腺肿瘤", '"salivary gland neoplasms"[MeSH Terms] OR "salivary gland tumor"[Title/Abstract]'),
    ("唾液腺肿瘤", '"salivary gland neoplasms"[MeSH Terms] OR "salivary gland tumor"[Title/Abstract]'),
    ("腮腺肿瘤", '"parotid neoplasm"[Title/Abstract] OR "parotid tumor"[Title/Abstract]'),
    ("颌下腺肿瘤", '"submandibular gland neoplasm"[Title/Abstract] OR "submandibular gland tumor"[Title/Abstract]'),
    ("颈部包块", '"neck mass"[Title/Abstract] OR "neck masses"[Title/Abstract]'),
    ("颈部肿块", '"neck mass"[Title/Abstract] OR "neck masses"[Title/Abstract]'),
    ("甲状腺结节", '"thyroid nodule"[Title/Abstract] OR "thyroid nodule"[MeSH Terms]'),
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
    return filter_by_query_focus(query, articles)


def build_pubmed_query(query: str) -> str:
    terms = query.replace("，", " ").replace(",", " ").strip()
    low = terms.lower()
    mapped = mapped_pubmed_terms(terms)
    translated = translated_pubmed_terms(terms)
    if mapped:
        base = mapped
    elif translated:
        base = translated
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
    return " AND ".join(unique_keep_order(matched))


def translated_pubmed_terms(query: str) -> str:
    matched = []
    for trigger, pubmed_terms in TERM_TRANSLATIONS:
        if trigger in query:
            matched.append(f"({pubmed_terms})")
    return " AND ".join(unique_keep_order(matched))


def query_focus_terms(query: str) -> list[str]:
    low = query.lower()
    terms: list[str] = []
    for triggers, _pubmed_terms, focus_terms in TOPIC_MAPPINGS:
        if any(trigger.lower() in low for trigger in triggers):
            terms.extend(focus_terms)
    return terms


def unique_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def filter_by_query_focus(query: str, articles: list[Article]) -> list[Article]:
    focus_terms = query_focus_terms(query)
    if not focus_terms:
        return articles
    title_matched = []
    abstract_matched = []
    for article in articles:
        title = article.title.lower()
        abstract = article.abstract.lower()
        if any(focus_term_matches(term, title) for term in focus_terms):
            title_matched.append(article)
        elif any(focus_term_matches(term, abstract) for term in focus_terms):
            abstract_matched.append(article)
    if query_requests_guidance(query):
        guidance_matched = [article for article in abstract_matched if article_looks_guidance(article)]
        return title_matched or guidance_matched
    return title_matched or abstract_matched


def query_requests_guidance(query: str) -> bool:
    low = query.lower()
    return any(word in low for word in ["guideline", "指南", "共识", "consensus", "recommendation", "建议"])


def article_looks_guidance(article: Article) -> bool:
    title = article.title.lower()
    pubtypes = {item.lower() for item in article.pubtypes}
    guidance_title_terms = ["guideline", "consensus", "recommendation", "recommendations", "statement", "position paper"]
    guidance_pubtypes = {"guideline", "practice guideline", "consensus development conference"}
    return any(term in title for term in guidance_title_terms) or bool(pubtypes & guidance_pubtypes)


def focus_term_matches(term: str, haystack: str) -> bool:
    if len(term) <= 3 or term.isupper():
        return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", haystack) is not None
    return term in haystack


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
