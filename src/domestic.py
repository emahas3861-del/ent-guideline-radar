from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class DomesticSource:
    name: str
    description: str
    url_template: str

    def url(self, query: str) -> str:
        return self.url_template.format(q=quote_plus(query))


DOMESTIC_SOURCES = [
    DomesticSource(
        name="医脉通指南",
        description="中文临床指南/专家共识入口，适合优先查国内指南与学会共识。",
        url_template="https://guide.medlive.cn/guideline/search?keywords={q}",
    ),
    DomesticSource(
        name="中华医学期刊网/中华医学会杂志社",
        description="中华系列期刊和学会共识常见发布入口，适合核对正式中文题名和出处。",
        url_template="https://www.yiigle.com/search?query={q}",
    ),
    DomesticSource(
        name="万方医学",
        description="国内医学期刊、指南、共识和学位论文检索入口，部分全文需机构权限。",
        url_template="https://med.wanfangdata.com.cn/search?q={q}",
    ),
    DomesticSource(
        name="CNKI 中国知网",
        description="国内期刊和会议文献检索入口，全文通常需要机构或个人权限。",
        url_template="https://kns.cnki.net/kns8s/defaultresult/index?kw={q}",
    ),
]


def domestic_query_terms(query: str) -> str:
    cleaned = " ".join((query or "").split())
    if not cleaned:
        cleaned = "耳鼻咽喉头颈外科 指南 共识"
    if not any(word in cleaned for word in ["指南", "共识", "规范", "推荐"]):
        cleaned = f"{cleaned} 指南 共识"
    return cleaned


def domestic_sources_text(query: str) -> str:
    terms = domestic_query_terms(query)
    lines = [
        "国内权威来源补充检索：",
        f"检索词：{terms}",
    ]
    for source in DOMESTIC_SOURCES:
        lines.append(f"- {source.name}: {source.url(terms)}")
        lines.append(f"  说明：{source.description}")
    lines.append("提示：国内数据库常有访问权限限制；机器人目前提供入口和题名线索，不绕过付费或机构权限。")
    return "\n".join(lines)
