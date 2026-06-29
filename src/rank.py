from __future__ import annotations

from src.pubmed import Article


HIGH_VALUE_TYPES = {
    "Practice Guideline": 100,
    "Guideline": 95,
    "Consensus Development Conference": 90,
    "Systematic Review": 70,
    "Meta-Analysis": 68,
    "Randomized Controlled Trial": 65,
    "Clinical Trial": 55,
    "Review": 35,
}

KEYWORDS = {
    "guideline": 30,
    "consensus": 25,
    "clinical practice": 25,
    "risk stratification": 20,
    "randomized": 15,
    "systematic review": 15,
    "meta-analysis": 15,
    "de-escalation": 12,
    "active surveillance": 12,
    "immunotherapy": 10,
    "molecular": 10,
}


def score_article(article: Article) -> int:
    score = 0
    for typ in article.pubtypes:
        score += HIGH_VALUE_TYPES.get(typ, 0)
    haystack = f"{article.title} {article.abstract}".lower()
    for word, value in KEYWORDS.items():
        if word in haystack:
            score += value
    if article.abstract:
        score += 5
    return score


def select_items(articles: list[Article], seen: set[str], max_items: int) -> list[Article]:
    unseen = [a for a in articles if a.id and a.id not in seen]
    dedup: dict[str, Article] = {}
    for item in unseen:
        key = item.doi.lower() if item.doi else item.pmid
        if key and key not in dedup:
            dedup[key] = item
    return sorted(dedup.values(), key=score_article, reverse=True)[:max_items]
