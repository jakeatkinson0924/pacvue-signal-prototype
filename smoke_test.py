"""Day 1 smoke tests: can we talk to Gemma, search the web, and get clean JSON back?"""

from dotenv import load_dotenv
from pydantic import BaseModel

from signal_agent.llm import ask_json, chat

load_dotenv()  # loads OLLAMA_API_KEY from .env for web search


def test_chat():
    print("1. Chat OK:", chat([{"role": "user", "content": "Say hello in one short sentence."}]).strip())


def test_search():
    import ollama

    try:
        results = ollama.web_search("Walmart Marketplace brand expansion 2026", max_results=3)
        for r in results.results:
            print("2. Search OK:", r.title, "|", r.url)
    except Exception as e:
        print("2. Search FAILED:", type(e).__name__, e)


class Demo(BaseModel):
    company: str
    signals: list[str]


def test_json():
    data = ask_json(
        [{"role": "user", "content": "Describe a fictional beauty brand expanding to Walmart."}],
        Demo,
    )
    print("3. JSON OK:", data.company, "|", len(data.signals), "signals")


if __name__ == "__main__":
    test_chat()
    test_search()
    test_json()
