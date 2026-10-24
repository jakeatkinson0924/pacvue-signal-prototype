"""Search queries for each buying signal. {company} is replaced with the company name.

🧑 Jake: these are drafts based on our brainstorm. Edit them freely, then rerun
`uv run python -m signal_agent "Boka"` to see how the evidence changes.
Tips: phrase them the way a press release, job post, or interview would.

The free Ollama plan limits web searches per hour, so the initial sweep uses one
query per signal. Swap in an alternate if a query isn't finding much.
"""

QUERIES: dict[str, list[str]] = {
    "retail_expansion": ["{company} now available at Walmart 2026"],
    "retail_media_hiring": ["{company} hiring retail media manager"],
    "amazon_launch": ["{company} launches new product line on Amazon"],
    "commerce_investment": ["{company} hires head of ecommerce OR chief digital officer"],
    "ad_complexity_pain": ["{company} retail media interview measurement multiple retailers"],
}

# Alternates to try (not run automatically):
#   retail_expansion:     "{company} expands to Target OR Walmart stores"
#   retail_media_hiring:  "{company} jobs ecommerce advertising Amazon Walmart"
#   amazon_launch:        "{company} Amazon exclusive launch 2026"
#   commerce_investment:  "{company} funding OR acquisition OR investment growth 2026"
#   ad_complexity_pain:   "{company} retail media agency review OR commerce agency of record"

# The test companies Jake picked (one per test type).
TEST_COMPANIES = [
    "Boka",               # strong: Amazon -> Target -> Walmart
    "Clearstem",          # newly expanding: Target Beauty Studio, Sept 2026
    "Lola from Rio",      # mixed: strong but partly older signals
    "My Flexy",           # small/weak: should not be over-ranked
    "Davids Toothpaste",  # edge case: appears in a competitor (Perpetua) case study
]
