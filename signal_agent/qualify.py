"""Qualification agent: score the five dimensions, then compute total, priority, and confidence.

The AI rates each dimension (0-10) with reasons. Python does the weighted math
and the confidence rules, so those parts are exact and explainable.
"""

from datetime import date

from .llm import ask_json
from .models import WEIGHTS, Evidence, Prospect, ScoreSet

SCORE_PROMPT = """You are qualifying "{company}" as a potential customer for Pacvue, a retail media and
commerce software platform (cross-retailer ad management for Amazon, Walmart, Instacart, Target and
others; automation; digital shelf analytics; measurement). Today is {today}.

Rate each dimension from 0 to 10 using ONLY the evidence below. Cite evidence by its [number].
- retail_expansion: Is the company selling across more retailers (e.g., new Walmart/Target/Amazon presence)?
- organizational_investment: Is it hiring or investing in ecommerce / retail media people or teams?
- media_complexity: How complex is its advertising likely to be (number of retailers, products, channels)?
- technology_opportunity: How likely is it to need a platform like Pacvue? Lower this if evidence shows
  it already uses a competing tool (e.g., Skai, Perpetua, Flywheel) or is very small.
- timing_urgency: How recent are the signals? Signals from the last 6 months score high; over a year old score low.

Rules: no evidence for a dimension means a low score (0-2) and say so. Facts count more than inferences.
Add flags for anything a salesperson must know (competitor tools, stale signals, company may be too small,
evidence mostly undated). Set identity_uncertain to true if any evidence may be about a different company
with a similar name, and score only the evidence that is clearly about {company}.

Evidence:
{evidence}"""


def format_evidence(evidence: list[Evidence]) -> str:
    return "\n".join(
        f"[{i}] ({ev.signal_type}, {ev.kind}, published {ev.published}) {ev.claim}" for i, ev in enumerate(evidence)
    ) or "(no evidence found)"


def weighted_total(prospect: Prospect) -> float:
    """Each 0-10 score is scaled by its weight; the result is 0-100."""
    return round(sum(s.score / 10 * WEIGHTS[s.dimension] * 100 for s in prospect.scores), 1)


def priority_for(total: float) -> str:
    return "High" if total >= 70 else "Medium" if total >= 45 else "Low"


def _is_recent(published: str, days: int = 365) -> bool:
    try:
        return (date.today() - date.fromisoformat(published)).days <= days
    except ValueError:  # "unknown" or a malformed date
        return False


def confidence_for(evidence: list[Evidence]) -> tuple[str, str]:
    """Rule-based confidence: how much evidence, how recent, and how much is fact vs. inference."""
    facts = [e for e in evidence if e.kind == "fact"]
    recent_facts = [e for e in facts if _is_recent(e.published)]
    signal_types = {e.signal_type for e in facts if e.signal_type != "other"}
    undated = sum(e.published == "unknown" for e in evidence)

    reason = (
        f"{len(facts)} facts, {len(evidence) - len(facts)} inferences; "
        f"{len(recent_facts)} facts dated within the last year; "
        f"{len(signal_types)} of 5 signal types covered; {undated} undated items."
    )
    if len(facts) >= 6 and len(recent_facts) >= 3 and len(signal_types) >= 3:
        return "High", reason
    if len(facts) >= 3 and len(recent_facts) >= 1:
        return "Medium", reason
    return "Low", reason


def qualify(prospect: Prospect) -> Prospect:
    """Score the prospect in place and return it."""
    result = ask_json(
        [{"role": "user", "content": SCORE_PROMPT.format(
            company=prospect.company, today=date.today().isoformat(), evidence=format_evidence(prospect.evidence)
        )}],
        ScoreSet,
    )
    # Keep exactly one score per dimension (in case the model repeats or skips one).
    by_dim = {s.dimension: s for s in result.scores}
    missing = [d for d in WEIGHTS if d not in by_dim]
    if missing:
        raise ValueError(f"Model skipped dimensions: {missing}")

    prospect.scores = [by_dim[d] for d in WEIGHTS]
    prospect.flags = result.flags
    prospect.total_score = weighted_total(prospect)
    prospect.priority = priority_for(prospect.total_score)
    prospect.confidence, prospect.confidence_reason = confidence_for(prospect.evidence)
    if result.identity_uncertain and prospect.confidence == "High":
        prospect.confidence = "Medium"
        prospect.confidence_reason += " Capped at Medium: some evidence may be about a different company."
    return prospect
