"""Strategy agent: turn the assessment into an account brief and an outreach draft."""

from datetime import date

from .llm import ask_json
from .models import AccountBrief, Prospect
from .qualify import format_evidence

PACVUE_CAPABILITIES = [
    "Cross-retailer retail media management (Amazon, Walmart, Instacart, Target and more) from one dashboard",
    "Campaign automation (rules for bids and budgets)",
    "Digital shelf analytics (inventory, Buy Box, product content, share of voice, pricing)",
    "Cross-retailer measurement and reporting",
]

BRIEF_PROMPT = """You are a Pacvue sales strategist writing an account brief about "{company}". Today is {today}.

Pacvue capabilities (only recommend from this list):
{capabilities}

Assessment: total score {total}/100 ({priority} priority), confidence {confidence} ({confidence_reason}).
Dimension scores:
{scores}
Flags: {flags}

Evidence:
{evidence}

Write the brief:
- why_attractive: 2-3 sentences, citing evidence by [number]. Separate facts from your inferences.
- relevant_capabilities: the 1-3 most relevant capabilities from the list, each with a short reason.
- likely_buyer: the role most likely to buy (e.g., "Head of Ecommerce"). Only name a person if the evidence names them.
- missing_info: what a salesperson still needs to find out.
- next_step: one concrete action. If priority or confidence is Low, recommend monitoring rather than outreach.
  If the company already uses a competing platform ({competitor}), recommend a "switch" approach:
  learn what the current tool doesn't cover (e.g., retailers, analytics) before pitching.
- outreach_draft: a short email (under 120 words) from a Pacvue rep to [Name], referencing one public signal.
  Do not invent facts, statistics, or results. Do not claim Pacvue guarantees outcomes."""


def write_brief(prospect: Prospect) -> AccountBrief:
    scores = "\n".join(f"- {s.dimension}: {s.score}/10 ({s.reason})" for s in prospect.scores)
    return ask_json(
        [{"role": "user", "content": BRIEF_PROMPT.format(
            company=prospect.company,
            today=date.today().isoformat(),
            capabilities="\n".join(f"- {c}" for c in PACVUE_CAPABILITIES),
            total=prospect.total_score,
            priority=prospect.priority,
            confidence=prospect.confidence,
            confidence_reason=prospect.confidence_reason,
            scores=scores,
            flags="; ".join(prospect.flags) or "none",
            competitor="confirmed" if prospect.uses_competitor else "not confirmed",
            evidence=format_evidence(prospect.evidence),
        )}],
        AccountBrief,
    )
