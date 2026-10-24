"""The agent loop: research, score, decide what to research next, repeat, then recommend.

This is what makes PacVue Signal "agentic": after each round the AI looks at what
it knows, picks its own follow-up searches, and decides when to stop.
"""

from datetime import date, datetime
from typing import Callable

from .llm import ask_json
from .models import Prospect, ResearchPlan, ResearchStep
from .qualify import format_evidence, qualify
from .research import _normalize, initial_research, run_queries
from .search import SearchUnavailable
from .strategy import write_brief

MAX_ROUNDS = 2  # kept small because the free plan limits web searches per hour

PLAN_PROMPT = """You are deciding the next research step for a Pacvue sales assessment of "{company}".
Today is {today}. This is follow-up round {round} of at most {max_rounds}.

Current assessment: {total}/100, confidence {confidence} ({confidence_reason}).
Scores:
{scores}
Flags: {flags}

Evidence so far:
{evidence}

Searches already run (do not repeat them):
{past_queries}

Identify the most important gaps, then choose 1-2 NEW web searches that would most change the assessment.
Useful kinds of follow-up:
- Amazon presence found but no Walmart/Target evidence: search whether its products are sold at Walmart or Target.
- No buyer identified: search for its head of ecommerce, retail media, or digital.
- Check whether it already uses a retail media platform (e.g., search "{company} Skai OR Perpetua OR Flywheel case study").
- Key signals undated or old: search for recent 2026 news.
- Evidence might be about a different company with a similar name: search to confirm identity.
If confidence is already High, only continue to check a key risk that hasn't been checked yet (most
importantly, whether it already uses a competing platform). Set stop=true (with no queries) if nothing
important is left to check, or if the remaining gaps are unlikely to be answered by public web searches.
Explain your reasoning in one or two sentences."""


def _plan_next(prospect: Prospect, round_no: int) -> ResearchPlan:
    past = [q for step in prospect.trail for q in step.queries]
    return ask_json(
        [{"role": "user", "content": PLAN_PROMPT.format(
            company=prospect.company,
            today=date.today().isoformat(),
            round=round_no,
            max_rounds=MAX_ROUNDS,
            total=prospect.total_score,
            confidence=prospect.confidence,
            confidence_reason=prospect.confidence_reason,
            scores="\n".join(f"- {s.dimension}: {s.score}/10 ({s.reason})" for s in prospect.scores),
            flags="; ".join(prospect.flags) or "none",
            evidence=format_evidence(prospect.evidence),
            past_queries="\n".join(f"- {q}" for q in past),
        )}],
        ResearchPlan,
    )


def _add_new_evidence(prospect: Prospect, found) -> int:
    """Add evidence we don't already have (same URL and same claim counts as a duplicate)."""
    seen = {(_normalize(e.source_url), e.claim.strip().lower()) for e in prospect.evidence}
    added = 0
    for ev in found:
        key = (_normalize(ev.source_url), ev.claim.strip().lower())
        if key not in seen:
            prospect.evidence.append(ev)
            seen.add(key)
            added += 1
    return added


def investigate_deeper(prospect: Prospect, rounds: int = MAX_ROUNDS, log: Callable[[str], None] = print) -> Prospect:
    """Run up to `rounds` follow-up rounds, letting the AI choose each search."""
    start = max((s.round for s in prospect.trail), default=0) + 1
    for round_no in range(start, start + rounds):
        plan = _plan_next(prospect, round_no)
        if plan.stop or not plan.queries:
            log(f"Agent chose to stop: {plan.reasoning}")
            prospect.trail.append(ResearchStep(round=round_no, decision=f"Stopped: {plan.reasoning}", queries=[]))
            break

        queries = plan.queries[:2]
        log(f"Round {round_no}: {plan.reasoning}")
        for q in queries:
            log(f"  search: {q}")
        try:
            found, _ = run_queries(prospect.company, queries, signal="; ".join(plan.gaps))
        except SearchUnavailable as err:
            log(f"Search unavailable; stopping follow-up research. ({err})")
            prospect.flags.append("Follow-up research incomplete: web search was unavailable (free-plan hourly limit).")
            prospect.trail.append(ResearchStep(round=round_no, decision=f"Planned: {plan.reasoning} Not run: web search unavailable.", queries=queries))
            break
        score_before, confidence_before = prospect.total_score or 0, prospect.confidence
        added = _add_new_evidence(prospect, found)
        qualify(prospect)

        prospect.trail.append(ResearchStep(
            round=round_no,
            decision=f"Gaps: {'; '.join(plan.gaps)}. {plan.reasoning}",
            queries=queries,
            new_evidence=added,
            score_after=prospect.total_score,
            confidence_after=prospect.confidence,
        ))
        log(f"  +{added} evidence -> score {prospect.total_score}, confidence {prospect.confidence}")
        if added == 0:
            log("No new evidence found; stopping.")
            prospect.trail[-1].decision += " Result: no new evidence found, so the agent stopped."
            break
        if abs((prospect.total_score or 0) - score_before) < 2 and prospect.confidence == confidence_before:
            log("Score changed by less than 2 points; more searching is unlikely to help. Stopping.")
            prospect.trail[-1].decision += " Result: assessment essentially unchanged, so the agent stopped (diminishing returns)."
            break

    prospect.brief = write_brief(prospect)
    prospect.updated_at = datetime.now().isoformat(timespec="seconds")
    return prospect


def investigate(company: str, rounds: int = MAX_ROUNDS, log: Callable[[str], None] = print) -> Prospect:
    """Full run: initial sweep, score, agentic follow-up, then account brief."""
    log(f"Researching {company}...")
    evidence, step = initial_research(company)
    prospect = Prospect(company=company, evidence=evidence, trail=[step])
    qualify(prospect)
    step.score_after, step.confidence_after = prospect.total_score, prospect.confidence
    log(f"Initial sweep: {len(evidence)} evidence -> score {prospect.total_score}, confidence {prospect.confidence}")
    return investigate_deeper(prospect, rounds=rounds, log=log)
