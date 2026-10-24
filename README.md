# PacVue Signal

**An AI growth-intelligence agent prototype.** It looks for public signs that a brand is becoming more sophisticated in retail media, investigates on its own, scores the opportunity, and recommends how Pacvue could engage, with a person approving any outreach.

> *How could Pacvue identify brands that are becoming more sophisticated in retail media before those brands actively start looking for software?*

Built by Jake Atkinson as a prototype. It uses only public web information and no Pacvue systems or customer data.

---

## How it works

```
Company name
   │
   ▼
Research agent ──► Qualification agent ──► Agent loop ──► Strategy agent ──► Human review
(5 signal types)   (5 weighted scores)     (decides what     (account brief +    (approve /
                                            to research next)  outreach draft)     reject)
```

1. **Discover / Research:** searches the web for the five buying signals in the brief: retail expansion (e.g., Walmart), retail media hiring, Amazon launches, commerce investment, and public ad-complexity pain. The AI turns results into **Evidence** records: a claim, its source URL, its date, and whether it's a **fact** or an **inference**.
2. **Evaluate:** the AI rates five dimensions from 0 to 10, with reasons and cited evidence. **Python computes the weighted total** (retail expansion 25%; organizational investment, media complexity and technology opportunity 20% each; timing 15%). Confidence is rule-based: how many facts there are, how recent, and how many signal types they cover.
3. **Decide (the agentic part):** the AI reviews its own assessment, names the gaps, and **chooses its own follow-up searches**. Examples: checking whether an Amazon-first brand is on Walmart yet, finding the likely buyer, or checking whether the brand already uses a competing tool. It rescores after each round and **stops** when there's no new evidence, when the score stops moving (diminishing returns), or when it hits the round limit. Every decision is logged in a **research trail**.
4. **Recommend:** an account brief (why the company is attractive, relevant Pacvue capabilities, likely buyer, what's missing, next step) plus a short outreach draft.
5. **Human judgment:** outreach starts as *pending*. A person approves or rejects it. **The app never sends anything.**

### Trust features
- **No invented sources:** evidence is dropped if its URL didn't appear in real search results.
- **Dates are never guessed:** a date comes from the source text or the URL; otherwise it's "unknown," and confidence goes down.
- **Facts and inferences are labeled separately** throughout the app.
- **A failed search never counts as "no evidence."** If search is unavailable, the run stops and nothing is saved.
- **Weights are hypotheses.** No predictive accuracy or revenue lift is claimed.

---

## Setup

Requirements: macOS/Linux, [uv](https://docs.astral.sh/uv/), and [Ollama](https://ollama.com) (signed in).

```bash
cd pacvue-signal
uv sync                      # installs Python 3.12 and packages
cp .env.example .env         # then add your OLLAMA_API_KEY (https://ollama.com/settings/keys)
ollama signin                # lets the local Ollama app use gemma4:cloud
```

## Run

```bash
uv run streamlit run app.py                        # dashboard
uv run python -m signal_agent "Boka"               # one company, in the terminal
uv run python -m signal_agent --all                # all test companies
uv run python smoke_test.py                        # check chat, search, and JSON
```

### Switching models
The code talks to the model with the OpenAI Python library, pointed at Ollama. To use OpenAI instead, change `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` in `.env`. No code changes are needed.

---

## Project layout

| File | Role |
|---|---|
| `app.py` | Streamlit dashboard |
| `signal_agent/queries.py` | Search queries per signal, plus the test companies |
| `signal_agent/search.py` | Ollama web search/fetch, cached to `data/cache/` |
| `signal_agent/research.py` | Research agent: search → Evidence, with the trust rule |
| `signal_agent/qualify.py` | Qualification agent: scores, weighted total, confidence |
| `signal_agent/agent.py` | The agent loop: plan follow-ups, rescore, stop |
| `signal_agent/strategy.py` | Strategy agent: account brief + outreach draft |
| `signal_agent/models.py` | Data shapes (Evidence, Prospect, …) and weights |
| `signal_agent/llm.py` | Model connection + reliable structured output |
| `signal_agent/store.py` | One JSON per company + `data/prospects.csv` |

---

## What worked, what didn't, what's next

**Worked**
- The agent connected signals on its own. For Boka, it found that a retail media job posted by the parent company Essor was *for Boka*.
- Follow-up research was genuinely adaptive: it checked for competing tools on high-scoring brands and looked for buyers when none were named.
- Caching made reruns instant and kept demos reliable.

**Didn't work at first (and how it was fixed)**
- **Gemma didn't strictly follow "JSON mode."** It wrapped its answers in code fences. Fix: strip the fences, validate with Pydantic, and retry once with the error message.
- **The free Ollama plan limits web searches per hour.** An early run hit the limit, and failed searches were wrongly scored as "no evidence." Fix: failures now stop the run honestly; queries were cut to one per signal and follow-ups to 2 rounds × 2 searches.
- **The agent kept searching after the answer stopped changing.** Fix: a diminishing-returns stop rule.

**Known limitations**
- Many sources (LinkedIn, company pages) have no visible date, so they're marked "unknown."
- Competitor-tool detection relies on public case studies, so "none found" is weak evidence.
- "Not found at Walmart" is always an inference: search can show presence, not absence.
- Scores vary somewhat between runs, because the AI's ratings aren't perfectly repeatable.

**With another month**
- Continuous monitoring of a list of brands, with alerts when a score changes materially.
- Matching discoveries to CRM (customer relationship management) records in Salesforce or HubSpot, to skip existing customers.
- Testing accuracy: compare recommendations with real sales outcomes (meetings, accepted leads, pipeline) and tune the weights.
- An edit step for outreach drafts, and a paid search tier for broader coverage.

## What production would require
- A paid model/search tier, or an enterprise search API, for volume.
- CRM integration and de-duplication against existing Pacvue customers.
- An evaluation set of known outcomes to validate the scoring.
- Logging, monitoring, and review of every outreach before anything is sent.
- Legal and privacy review of the data sources.
