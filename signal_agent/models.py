"""The shape of every record PacVue Signal creates.

Pydantic checks that data matches these shapes. If the AI returns something
malformed (a score of 15, a missing source URL), we find out immediately
instead of showing bad data in the demo.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# The five buying signals from the project brief (Step 1 - Discover).
SignalType = Literal[
    "retail_expansion",     # e.g., expanding into Walmart
    "retail_media_hiring",  # e.g., hiring a director of retail media
    "amazon_launch",        # e.g., new product category on Amazon
    "commerce_investment",  # e.g., investing in ecommerce teams or agencies
    "ad_complexity_pain",   # e.g., publicly struggling to manage ads across retailers
    "other",
]

# The five scoring dimensions and their weights (brief, Step 3 - Evaluate).
# These are starting guesses, not proven predictors. Say so in the demo.
Dimension = Literal[
    "retail_expansion",
    "organizational_investment",
    "media_complexity",
    "technology_opportunity",
    "timing_urgency",
]
WEIGHTS: dict[str, float] = {
    "retail_expansion": 0.25,
    "organizational_investment": 0.20,
    "media_complexity": 0.20,
    "technology_opportunity": 0.20,
    "timing_urgency": 0.15,
}


class Evidence(BaseModel):
    """One claim found during research, tied to where it came from."""

    claim: str = Field(description="One sentence stating what was found.")
    source_url: str = Field(description="Must be a URL that appeared in the search results.")
    source_title: str = ""
    published: str = Field("unknown", description="Publish date as YYYY-MM-DD, or 'unknown'. Never guess.")
    signal_type: SignalType
    kind: Literal["fact", "inference"] = Field(
        description="'fact' if the source states it directly; 'inference' if it is our interpretation."
    )


class EvidenceList(BaseModel):
    """Wrapper so the AI can return several Evidence items at once."""

    items: list[Evidence]


class DimensionScore(BaseModel):
    """The AI's 0-10 rating for one dimension, with its reasoning."""

    dimension: Dimension
    score: int = Field(ge=0, le=10)
    reason: str = Field(description="One sentence explaining the score.")
    evidence_ids: list[int] = Field(default_factory=list, description="Positions of supporting items in the evidence list.")


class ScoreSet(BaseModel):
    """What the Qualification agent returns: five scores plus any warnings."""

    scores: list[DimensionScore]
    flags: list[str] = Field(
        default_factory=list,
        description="Important caveats, e.g. 'appears in a competitor's case study' or 'signals are over a year old'.",
    )
    identity_uncertain: bool = Field(
        False, description="True if some evidence may be about a different company with a similar name."
    )


class ResearchPlan(BaseModel):
    """What the agent decides to research next (the 'agentic' step)."""

    gaps: list[str] = Field(description="The most important missing information.")
    reasoning: str = Field(description="Why these searches are the best next step, or why to stop.")
    queries: list[str] = Field(default_factory=list, description="1-2 new web searches. Empty if stopping.")
    stop: bool = Field(description="True if more searching is unlikely to change the assessment.")


class ResearchStep(BaseModel):
    """One entry in the research trail: what the agent decided and why."""

    round: int
    decision: str = Field(description="What the agent chose to do next and why.")
    queries: list[str]
    new_evidence: int = 0
    score_after: float | None = None
    confidence_after: str | None = None


class AccountBrief(BaseModel):
    """The recommendation (brief, Step 4) plus an outreach draft (Step 5)."""

    why_attractive: str
    relevant_capabilities: list[str]
    likely_buyer: str
    missing_info: list[str]
    next_step: str
    outreach_draft: str
    approval: Literal["pending", "approved", "rejected"] = "pending"  # a human decides; the app never sends


class Prospect(BaseModel):
    """Everything PacVue Signal knows about one company."""

    company: str
    evidence: list[Evidence] = Field(default_factory=list)
    scores: list[DimensionScore] = Field(default_factory=list)
    total_score: float | None = None  # 0-100, calculated in Python, not by the AI
    priority: Literal["High", "Medium", "Low"] | None = None
    confidence: Literal["High", "Medium", "Low"] | None = None
    confidence_reason: str = ""
    flags: list[str] = Field(default_factory=list)
    trail: list[ResearchStep] = Field(default_factory=list)
    brief: AccountBrief | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
