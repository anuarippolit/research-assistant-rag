import re

CHUNK_SIZE = 1600     # characters (~400 tokens; stays under bge-small's 512-token limit)
CHUNK_OVERLAP = 300   # characters shared by neighbouring chunks (~75 tokens, ~20%)


def clean_text(text: str) -> str:
    # remove whitespaces and new lines
    return re.sub(r"\s+", " ", text).strip()


def drop_build_steps(pages: list[dict], threshold: float = 0.8) -> list[dict]:
    # for animated slides, drop slides with the same text that sequentially apper
    kept = []
    for i, page in enumerate(pages):
        if i + 1 < len(pages):
            words = set(clean_text(page["text"]).split())
            next_words = set(clean_text(pages[i + 1]["text"]).split())
            if words and len(words & next_words) / len(words) >= threshold:
                continue  # the next page contains this one -> it is an earlier step
        kept.append(page)
    return kept


def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Input:  [{"page": 1, "text": "..."}, ...]   (output of parse_pdf)
    Output: [{"page": 1, "chunk_index": 0, "text": "..."}, ...]
    """
    step = CHUNK_SIZE - CHUNK_OVERLAP
    chunks = []
    for page in pages:
        text = clean_text(page["text"])
        for start in range(0, len(text), step):
            piece = text[start:start + CHUNK_SIZE]
            chunks.append({
                "page": page["page"],
                "chunk_index": len(chunks),  # global index within the document
                "text": piece,
            })
            if start + CHUNK_SIZE >= len(text):  # this chunk reached the end of the page
                break
    return chunks
