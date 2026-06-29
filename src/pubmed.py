from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta


BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class Article:
    id: str
    topic: str
    title: str
    journal: str
    pubdate: str
    authors: str
    doi: str
    pmid: str
    url: str
    abstract: str
    pubtypes: list[str]
    pmcid: str = ""
    pmc_release: str = ""


def _get_json(endpoint: str, params: dict, retries: int = 2) -> dict:
    api_key = os.getenv("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"PubMed request failed: {last_error}")


def search_pmids(query: str, lookback_days: int, retmax: int = 30) -> list[str]:
    start = date.today() - timedelta(days=lookback_days)
    dated_query = f"({query}) AND ({start:%Y/%m/%d}[Date - Publication] : 3000[Date - Publication])"
    data = _get_json(
        "esearch.fcgi",
        {
            "db": "pubmed",
            "retmode": "json",
            "sort": "pub date",
            "retmax": str(retmax),
            "term": dated_query,
        },
    )
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_article_details(pmids: list[str], topic_by_pmid: dict[str, str]) -> list[Article]:
    if not pmids:
        return []
    url = f"{BASE}/efetch.fcgi?{urllib.parse.urlencode({'db': 'pubmed', 'retmode': 'xml', 'id': ','.join(pmids)})}"
    api_key = os.getenv("NCBI_API_KEY")
    if api_key:
        url += "&" + urllib.parse.urlencode({"api_key": api_key})

    import xml.etree.ElementTree as ET

    with urllib.request.urlopen(url, timeout=40) as resp:
        root = ET.fromstring(resp.read())

    articles: list[Article] = []
    for node in root.findall(".//PubmedArticle"):
        pmid = _text(node, ".//PMID")
        article_node = node.find(".//Article")
        title = _text(article_node, "ArticleTitle") if article_node is not None else ""
        journal = _text(article_node, "Journal/Title") if article_node is not None else ""
        pubdate = _pubdate(article_node)
        authors = _authors(article_node)
        abstract = _abstract(article_node)
        pubtypes = [_clean_text(x) for x in article_node.findall(".//PublicationType")] if article_node is not None else []
        doi = _article_doi(article_node)
        pmcid = ""
        for aid in node.findall("./PubmedData/ArticleIdList/ArticleId"):
            id_type = aid.attrib.get("IdType")
            value = _clean_text(aid)
            if id_type == "doi" and not doi:
                doi = value
            elif id_type in {"pmc", "pmcid"}:
                pmcid = value.replace("pmc-id:", "").replace(";", "").strip().upper()
        pmc_release = _pmc_release_date(node)
        item_id = f"PMID:{pmid}" if pmid else f"DOI:{doi}"
        articles.append(
            Article(
                id=item_id,
                topic=topic_by_pmid.get(pmid, "Uncategorized"),
                title=title,
                journal=journal,
                pubdate=pubdate,
                authors=authors,
                doi=doi,
                pmid=pmid,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                abstract=abstract,
                pubtypes=pubtypes,
                pmcid=pmcid,
                pmc_release=pmc_release,
            )
        )
    return articles


def search_topics(topics: list[dict], lookback_days: int, per_topic: int = 25) -> list[Article]:
    pmids: list[str] = []
    topic_by_pmid: dict[str, str] = {}
    for topic in topics:
        found = search_pmids(topic["query"], lookback_days, per_topic)
        for pmid in found:
            if pmid not in topic_by_pmid:
                pmids.append(pmid)
                topic_by_pmid[pmid] = topic["name"]
        time.sleep(0.35)
    return fetch_article_details(pmids, topic_by_pmid)


def _text(node, path: str) -> str:
    if node is None:
        return ""
    found = node.find(path)
    return _clean_text(found) if found is not None else ""


def _clean_text(node) -> str:
    return " ".join("".join(node.itertext()).split())

def _article_doi(article_node) -> str:
    if article_node is None:
        return ""
    for item in article_node.findall("ELocationID"):
        if item.attrib.get("EIdType") == "doi":
            return _clean_text(item)
    return ""


def _pmc_release_date(node) -> str:
    for item in node.findall("./PubmedData/History/PubMedPubDate"):
        if item.attrib.get("PubStatus") == "pmc-release":
            year = item.findtext("Year", default="")
            month = item.findtext("Month", default="")
            day = item.findtext("Day", default="")
            return "-".join(x.zfill(2) if len(x) == 1 else x for x in [year, month, day] if x)
    return ""

def _pubdate(article_node) -> str:
    if article_node is None:
        return ""
    pub = article_node.find("Journal/JournalIssue/PubDate")
    if pub is None:
        return ""
    year = pub.findtext("Year", default="")
    month = pub.findtext("Month", default="")
    day = pub.findtext("Day", default="")
    medline = pub.findtext("MedlineDate", default="")
    return " ".join(x for x in [year, month, day] if x) or medline


def _authors(article_node) -> str:
    if article_node is None:
        return ""
    author_nodes = article_node.findall(".//Author")
    names = []
    for author in author_nodes[:8]:
        last = author.findtext("LastName", default="")
        initials = author.findtext("Initials", default="")
        collective = author.findtext("CollectiveName", default="")
        name = collective or " ".join(x for x in [last, initials] if x)
        if name:
            names.append(name)
    if len(author_nodes) > 8:
        names.append("et al.")
    return ", ".join(names)


def _abstract(article_node) -> str:
    if article_node is None:
        return ""
    parts = []
    for item in article_node.findall(".//AbstractText"):
        label = item.attrib.get("Label")
        text = _clean_text(item)
        if text:
            parts.append(f"{label}: {text}" if label else text)
    return "\n".join(parts)
