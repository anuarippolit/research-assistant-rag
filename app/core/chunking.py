import re

CHUNK_SIZE = 1600     # characters (~400 tokens; stays under bge-small's 512-token limit)
CHUNK_OVERLAP = 300   # characters shared by neighbouring chunks (~75 tokens, ~20%)


def clean_text(text: str) -> str:
    """Collapse runs of whitespace/newlines from PDF extraction into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def chunk_pages(pages: list[dict]) -> list[dict]:
    """Split each page into overlapping chunks.

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
