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

ENT_TERMS = {
    "otolaryngology", "head and neck", "laryngeal", "larynx", "oropharyngeal", "hypopharyngeal",
    "nasopharyngeal", "oral cavity", "salivary", "thyroid", "neck mass", "vocal fold", "dysphonia",
    "dysphagia", "tracheostomy", "upper airway", "sleep apnea", "tonsillectomy", "adenoidectomy",
    "otitis", "hearing", "cochlear", "cholesteatoma", "vestibular", "meniere", "bppv", "vertigo",
    "tinnitus", "rhinology", "rhinosinusitis", "sinusitis", "nasal", "epistaxis", "olfaction",
    "allergic rhinitis", "pediatric otolaryngology", "cleft palate", "ear", "nose", "throat",
}

OFF_TOPIC_TERMS = {
    "achalasia", "poem", "ards", "delirium", "pertussis", "copd", "asthma", "peep",
    "thoracic", "abdominal", "intubation sedative", "etomidate", "ketamine", "propofol",
    "remethylation", "homocysteine", "soft tissue sarcoma", "extremity", "trunk",
}


def is_relevant(article: Article) -> bool:
    haystack = f"{article.topic} {article.title} {article.abstract}".lower()
    has_ent = any(term in haystack for term in ENT_TERMS)
    has_off_topic = any(term in haystack for term in OFF_TOPIC_TERMS)
    if has_ent:
        return True
    return not has_off_topic


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
    if not is_relevant(article):
        score -= 200
    return score


def select_items(articles: list[Article], seen: set[str], max_items: int) -> list[Article]:
    unseen = [a for a in articles if a.id and a.id not in seen and is_relevant(a)]
    dedup: dict[str, Article] = {}
    for item in unseen:
        key = item.doi.lower() if item.doi else item.pmid
        if key and key not in dedup:
            dedup[key] = item
    return sorted(dedup.values(), key=score_article, reverse=True)[:max_items]
