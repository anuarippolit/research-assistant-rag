import json
import re
import sys
from pathlib import Path

from app.core.chat import answer
from app.core.prompts import NOT_FOUND_MESSAGE
from eval.run_retrieval import is_hit

QUESTION_PATH = Path(__file__).parent / "questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

# matches "[file.pdf, p. 12]" and captures the file name and the page number
CITATION = re.compile(r"\[([^\],]+), p\. (\d+)\]")


def extract_citations(text: str) -> list[dict]:
    # see [a.pdf, p. 5]' -> [{"filename": "a.pdf", "page": 5}] (same shape is_hit expects)
    return [{"filename": name, "page": int(page)} for name, page in CITATION.findall(text)]


def ids(rows: list[dict]) -> list[str]:
    return [r["id"] for r in rows]


def report(rows: list[dict]) -> None:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    answered = [r for r in answerable if not r["refused"]]

    correct_refusals = [r for r in unanswerable if r["refused"]]
    false_refusals = [r for r in answerable if r["refused"]]
    no_citation = [r for r in answered if not r["has_citation"]]
    wrong_citation = [r for r in answered if r["has_citation"] and not r["citation_correct"]]

    print(f"\ncorrect refusals (no answer in sources): {len(correct_refusals)}/{len(unanswerable)}")
    print(f"false refusals (answer exists, model refused): {len(false_refusals)}/{len(answerable)}")
    print(f"answers with at least one citation: {len(answered) - len(no_citation)}/{len(answered)}")
    print(f"answers citing a correct page: {len(answered) - len(no_citation) - len(wrong_citation)}/{len(answered)}")

    print("\nanswered but should have refused:", ids([r for r in unanswerable if not r["refused"]]))
    print("refused but had an answer:       ", ids(false_refusals))
    print("no citation:                      ", ids(no_citation))
    print("cited wrong page:                 ", ids(wrong_citation))


def main(label: str) -> None:
    questions = json.loads(QUESTION_PATH.read_text())
    rows = []

    for q in questions:
        result = answer(q["question"])
        text = result["answer"]
        citations = extract_citations(text)
        rows.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "answerable": q["answerable"],
            "answer": text,
            "refused": NOT_FOUND_MESSAGE in text,
            "has_citation": bool(citations),
            "citation_correct": any(is_hit(c, q["expected"]) for c in citations),
            "sources": result["sources"],
        })
        print(f"{q['id']} done")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"answers_{label}.json"
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"saved to {out}")

    report(rows)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "before")
