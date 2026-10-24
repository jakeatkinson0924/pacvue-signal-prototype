"""Research agent: search for buying signals and turn results into Evidence."""

import re

from .llm import ask_json
from .models import Evidence, EvidenceList, ResearchStep
from .queries import QUERIES
from .search import web_search

EXTRACT_PROMPT = """You are a research analyst for Pacvue, a retail media software company.
From the search results below, extract evidence about the company "{company}".
These searches focused on: {signal}.

Rules:
- Only include results that are clearly about {company} (not a similarly named company).
- Each claim is one sentence stating what the source says.
- source_url must be copied exactly from a result below.
- published: use a date only if it appears in the result text (YYYY-MM-DD); otherwise "unknown". Never guess.
- kind: "fact" if the source states it directly; "inference" if it is your interpretation.
- signal_type: the best fit of retail_expansion, retail_media_hiring, amazon_launch,
  commerce_investment, ad_complexity_pain, or other.
- If the results show the company does NOT appear somewhere (e.g., no Walmart listing found),
  you may record that as kind "inference", citing the search result you checked.
- If nothing relevant is found, return {{"items": []}}.

Search results:
{results}"""


def _normalize(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _date_from_url(url: str) -> str | None:
    """Many news URLs contain the date, e.g. /2026/03/31/. That's a fact we can use."""
    m = re.search(r"/(20\d\d)/(\d{1,2})/(\d{1,2})/", url)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def run_queries(company: str, queries: list[str], signal: str) -> tuple[list[Evidence], list[dict]]:
    """Search, then extract Evidence. Returns (evidence, raw results)."""
    results: dict[str, dict] = {}
    for q in queries:
        for r in web_search(q.replace("{company}", company)):
            results.setdefault(_normalize(r["url"]), r)  # skip duplicate URLs

    if not results:
        return [], []

    formatted = "\n\n".join(
        f"[{i}] {r['title']}\nURL: {r['url']}\n{r['content'][:800]}" for i, r in enumerate(results.values(), 1)
    )
    extracted = ask_json(
        [{"role": "user", "content": EXTRACT_PROMPT.format(company=company, signal=signal, results=formatted)}],
        EvidenceList,
    )

    kept = []
    for ev in extracted.items:
        # Trust rule: drop any evidence whose URL didn't come from a real search result.
        source = results.get(_normalize(ev.source_url))
        if source is None:
            print(f"  ! dropped evidence with unverified URL: {ev.source_url}")
            continue
        ev.source_title = ev.source_title or source["title"]
        if ev.published == "unknown" and (d := _date_from_url(ev.source_url)):
            ev.published = d
        kept.append(ev)
    return kept, list(results.values())


def initial_research(company: str) -> tuple[list[Evidence], ResearchStep]:
    """Round 0: sweep all five signal types with the queries in queries.py."""
    evidence: list[Evidence] = []
    all_queries: list[str] = []
    for signal, templates in QUERIES.items():
        print(f"  searching: {signal}")
        found, _ = run_queries(company, templates, signal)
        evidence.extend(found)
        all_queries += [t.replace("{company}", company) for t in templates]

    step = ResearchStep(
        round=0,
        decision="Initial sweep: search all five buying-signal types from the brief.",
        queries=all_queries,
        new_evidence=len(evidence),
    )
    return evidence, step
