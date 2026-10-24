"""Run from the terminal:

    uv run python -m signal_agent "Company Name"     # investigate one company
    uv run python -m signal_agent --all              # investigate all test companies
"""

import sys

from . import store
from .agent import investigate
from .queries import TEST_COMPANIES
from .search import SearchUnavailable


def report(company: str) -> None:
    p = investigate(company)
    path = store.save(p)
    print(f"\n=== {p.company}: {p.total_score}/100 ({p.priority} priority), confidence {p.confidence} ===")
    for s in p.scores:
        print(f"  {s.dimension:<26} {s.score:>2}/10  {s.reason}")
    for f in p.flags:
        print(f"  ! {f}")
    print(f"  Next step: {p.brief.next_step if p.brief else '-'}")
    print(f"  Saved to {path}\n")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    companies = TEST_COMPANIES if sys.argv[1] == "--all" else [sys.argv[1]]
    for company in companies:
        try:
            report(company)
        except SearchUnavailable as err:
            # Don't save a half-researched company as if it had no evidence.
            print(f"\nStopped at {company}: {err}")
            print("Nothing was saved for this company. Searches done so far are cached; rerun later.")
            sys.exit(2)


if __name__ == "__main__":
    main()
