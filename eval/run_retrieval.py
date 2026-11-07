import json
import re
from pathlib import Path

from app.core.embeddings import embed_query
from app.db.vector_store import search_chunks

QUESTION_PATH = Path(__file__).parent / "questions.json"
KS = [1, 3, 5]


def is_hit(r: dict, expected: list[dict]) -> bool:
    for source in expected:
        if r["filename"] == source["file"]:
            for a, b in source["pages"]:
                if a <= r["page"] <= b:
                    return True
    return False


def slide_id(r: dict) -> tuple:
    match = re.search(r"(\d+) / \d+\s*$", r["text"])
    return (r["filename"], match.group(1) if match else r["page"])


def main() -> None:
    questions = json.loads(QUESTION_PATH.read_text())
    answerable = [q for q in questions if q["answerable"]]

    hits = [0] * len(KS)   # per k: how many questions had a correct page in the top k
    unique_slides = 0      # total distinct slides in the top 5, summed over questions
    misses = []

    for q in answerable:
        results = search_chunks(embed_query(q["question"]), k=max(KS))

        for i, k in enumerate(KS):
            if any(is_hit(r, q["expected"]) for r in results[:k]):
                hits[i] += 1

        if not any(is_hit(r, q["expected"]) for r in results):
            misses.append(q["id"])

        unique_slides += len({slide_id(r) for r in results})

    n = len(answerable)
    print("   ".join(f"recall@{k}: {hits[i] / n:.2f}" for i, k in enumerate(KS)))
    print(f"unique slides in top-{max(KS)} (avg): {unique_slides / n:.2f}")
    print(f"misses@{max(KS)}: {misses}")


if __name__ == "__main__":
    main()
