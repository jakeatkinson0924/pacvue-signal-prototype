"""Web search and page fetch through Ollama, with every result saved to disk.

Saving (caching) results means a repeated search is instant and free, and the
demo still works if the internet or Ollama is slow.
"""

import hashlib
import json
from pathlib import Path

import ollama
from dotenv import load_dotenv

load_dotenv()  # web search needs OLLAMA_API_KEY from .env

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SearchUnavailable(Exception):
    """Search failed (e.g., the free plan's hourly limit). Never treat this as 'nothing found'."""


def _cache_path(kind: str, key: str) -> Path:
    return CACHE_DIR / f"{kind}_{hashlib.sha1(key.encode()).hexdigest()[:16]}.json"


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Return a list of {title, url, content} results for a query."""
    path = _cache_path("search", f"{query}|{max_results}")
    if path.exists():
        return json.loads(path.read_text())

    try:
        response = ollama.web_search(query, max_results=max_results)
        results = [{"title": r.title, "url": r.url, "content": r.content} for r in response.results]
    except Exception as err:
        # Stop here instead of returning [] so a failure is never mistaken for "no evidence".
        raise SearchUnavailable(f"Web search failed for {query!r}: {err}") from err

    path.write_text(json.dumps(results, indent=2))
    return results


def web_fetch(url: str) -> dict:
    """Return {title, content} for one page, or an empty dict if it can't be fetched."""
    path = _cache_path("fetch", url)
    if path.exists():
        return json.loads(path.read_text())

    try:
        response = ollama.web_fetch(url)
        page = {"title": response.title, "content": response.content}
    except Exception as err:
        print(f"  ! fetch failed for {url}: {err}")
        return {}

    path.write_text(json.dumps(page, indent=2))
    return page
