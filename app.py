"""PacVue Signal dashboard.  Run:  uv run streamlit run app.py"""

import pandas as pd
import streamlit as st

from signal_agent import store
from signal_agent.agent import investigate, investigate_deeper
from signal_agent.models import WEIGHTS, Prospect
from signal_agent.search import SearchUnavailable

st.set_page_config(page_title="PacVue Signal", page_icon="📡", layout="wide")

DIMENSION_NAMES = {
    "retail_expansion": "Retail expansion",
    "organizational_investment": "Organizational investment",
    "media_complexity": "Media complexity",
    "technology_opportunity": "Technology opportunity",
    "timing_urgency": "Timing and urgency",
}
LEVEL_ICON = {"High": "▲", "Medium": "◆", "Low": "▼", None: "–"}  # shape + word, never color alone


def level(value: str | None) -> str:
    return f"{LEVEL_ICON.get(value, '–')} {value or 'n/a'}"


def run_with_status(label: str, fn) -> Prospect | None:
    """Run an agent step with live progress; surface search-limit errors honestly."""
    with st.status(label, expanded=True) as status:
        try:
            result = fn(lambda msg: status.write(msg))
        except SearchUnavailable as err:
            status.update(label="Web search unavailable", state="error")
            st.error(f"{err}\n\nNothing was saved. The free plan limits searches per hour; try again later.")
            return None
        status.update(label="Done", state="complete")
    store.save(result)
    return result


# ---------- Sidebar: add a company ----------
with st.sidebar:
    st.header("Investigate a company")
    new_company = st.text_input("Company name", placeholder="e.g., Boka")
    if st.button("Run agent", type="primary", disabled=not new_company.strip()):
        if run_with_status(f"Investigating {new_company}...", lambda log: investigate(new_company.strip(), log=log)):
            st.rerun()
    st.caption(
        "Uses live web searches (limited per hour on the free plan). "
        "Model: Gemma 4 via Ollama. PacVue Signal recommends; it never contacts anyone."
    )

# ---------- Header ----------
st.title("📡 PacVue Signal")
st.markdown(
    "**How could Pacvue identify brands becoming more sophisticated in retail media "
    "before they start looking for software?**  \n"
    "An AI agent that finds buying signals, investigates, scores, and recommends, with a person approving every outreach."
)

prospects = store.load_all()
if not prospects:
    st.info("No prospects yet. Add a company in the sidebar to run the agent.")
    st.stop()

# ---------- Ranked prospect list ----------
st.subheader("Ranked prospects")
table = pd.DataFrame([{
    "Rank": i,
    "Company": p.company,
    "Score": p.total_score or 0,
    "Priority": level(p.priority),
    "Confidence": level(p.confidence),
    "Evidence": len(p.evidence),
    "Flags": len(p.flags),
    "Outreach": (p.brief.approval.capitalize() if p.brief else "–"),
} for i, p in enumerate(prospects, 1)])
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "Score": st.column_config.ProgressColumn("Score (0-100)", min_value=0, max_value=100, format="%.0f"),
        "Evidence": st.column_config.NumberColumn("Evidence items"),
    },
)

# ---------- Company detail ----------
st.divider()
names = [p.company for p in prospects]
choice = st.selectbox("Company detail", names)
p = next(x for x in prospects if x.company == choice)

head, action = st.columns([4, 1])
with head:
    st.header(p.company)
with action:
    st.write("")
    if st.button("🔎 Investigate more deeply", width="stretch"):
        if run_with_status("Agent is planning follow-up research...", lambda log: investigate_deeper(p, rounds=1, log=log)):
            st.rerun()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Opportunity score", f"{p.total_score:.0f}/100" if p.total_score is not None else "–")
m2.metric("Priority", level(p.priority))
m3.metric("Confidence", level(p.confidence))
m4.metric("Evidence items", len(p.evidence))
st.caption(f"Confidence basis: {p.confidence_reason}  ·  Last updated {p.updated_at}")
for flag in p.flags:
    st.warning(flag, icon="⚠️")

tab_scores, tab_evidence, tab_trail, tab_brief = st.tabs(
    ["Score breakdown", "Evidence", "Research trail", "Account brief & outreach"]
)

with tab_scores:
    rows = [{
        "Dimension": DIMENSION_NAMES[s.dimension],
        "Weight": f"{WEIGHTS[s.dimension]:.0%}",
        "Score": s.score,
        "Points": round(s.score / 10 * WEIGHTS[s.dimension] * 100, 1),
        "Why": s.reason,
        "Evidence": ", ".join(f"[{i}]" for i in s.evidence_ids),
    } for s in p.scores]
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Score": st.column_config.ProgressColumn("Score (0-10)", min_value=0, max_value=10, format="%d"),
            "Points": st.column_config.NumberColumn("Points toward total", format="%.1f"),
            "Why": st.column_config.TextColumn("Why", width="large"),
        },
    )
    st.caption(
        "The AI rates each dimension; Python computes the total (score ÷ 10 × weight). "
        "Weights are starting hypotheses from the brief, not validated predictors of conversion."
    )

with tab_evidence:
    show_inferences = st.toggle("Include inferences", value=True)
    ev_rows = [{
        "#": i,
        "Claim": e.claim,
        "Fact or inference": "Fact" if e.kind == "fact" else "Inference",
        "Signal": e.signal_type.replace("_", " "),
        "Published": e.published,
        "Source": e.source_url,
    } for i, e in enumerate(p.evidence) if show_inferences or e.kind == "fact"]
    if ev_rows:
        st.dataframe(
            pd.DataFrame(ev_rows),
            hide_index=True,
            width="stretch",
            column_config={
                "Claim": st.column_config.TextColumn("Claim", width="large"),
                "Source": st.column_config.LinkColumn("Source"),
            },
        )
    else:
        st.info("No evidence found.")
    st.caption("Every item links to a page that appeared in real search results. Dates are never guessed.")

with tab_trail:
    for step in p.trail:
        title = "Initial sweep" if step.round == 0 else f"Follow-up round {step.round}"
        with st.container(border=True):
            st.markdown(f"**{title}**: {step.decision}")
            if step.queries:
                st.markdown("Searches: " + " · ".join(f"`{q}`" for q in step.queries))
            outcome = f"+{step.new_evidence} evidence"
            if step.score_after is not None:
                outcome += f" → score {step.score_after:.0f}, confidence {step.confidence_after}"
            if step.queries:
                st.caption(outcome)

with tab_brief:
    b = p.brief
    if not b:
        st.info("No brief yet.")
    else:
        left, right = st.columns([3, 2])
        with left:
            st.markdown(f"**Why this account may be attractive**  \n{b.why_attractive}")
            st.markdown("**Relevant Pacvue capabilities**")
            st.markdown("\n".join(f"- {c}" for c in b.relevant_capabilities))
            st.markdown(f"**Likely buyer:** {b.likely_buyer}")
            st.markdown("**Still unknown**")
            st.markdown("\n".join(f"- {m}" for m in b.missing_info) or "- Nothing listed")
            st.markdown(f"**Recommended next step:** {b.next_step}")
        with right:
            st.markdown("**Outreach draft**")
            st.text_area("Outreach draft", b.outreach_draft, height=260, label_visibility="collapsed", disabled=True)
            st.markdown(f"**Status:** {b.approval.capitalize()}")
            a1, a2 = st.columns(2)
            if a1.button("✅ Approve", width="stretch", disabled=b.approval == "approved"):
                b.approval = "approved"
                store.save(p)
                st.rerun()
            if a2.button("❌ Reject", width="stretch", disabled=b.approval == "rejected"):
                b.approval = "rejected"
                store.save(p)
                st.rerun()
            st.caption("Approving only marks the draft as ready. PacVue Signal never sends messages; a person does.")
