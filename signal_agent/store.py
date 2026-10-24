"""Save and load prospects: one JSON file per company, plus a CSV summary for the ranked list."""

import csv
import re
from pathlib import Path

from .models import Prospect

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ASSESSMENTS = DATA_DIR / "assessments"
SUMMARY_CSV = DATA_DIR / "prospects.csv"
ASSESSMENTS.mkdir(parents=True, exist_ok=True)

CSV_FIELDS = ["company", "total_score", "priority", "confidence", "evidence_count", "approval", "updated_at"]


def slug(company: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")


def save(prospect: Prospect) -> Path:
    path = ASSESSMENTS / f"{slug(prospect.company)}.json"
    path.write_text(prospect.model_dump_json(indent=2))
    _rebuild_csv()
    return path


def load(company: str) -> Prospect | None:
    path = ASSESSMENTS / f"{slug(company)}.json"
    return Prospect.model_validate_json(path.read_text()) if path.exists() else None


def load_all() -> list[Prospect]:
    """All saved prospects, highest score first."""
    prospects = [Prospect.model_validate_json(p.read_text()) for p in ASSESSMENTS.glob("*.json")]
    return sorted(prospects, key=lambda p: p.total_score or 0, reverse=True)


def _rebuild_csv() -> None:
    with SUMMARY_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for p in load_all():
            writer.writerow({
                "company": p.company,
                "total_score": p.total_score,
                "priority": p.priority,
                "confidence": p.confidence,
                "evidence_count": len(p.evidence),
                "approval": p.brief.approval if p.brief else "",
                "updated_at": p.updated_at,
            })
