from pathlib import Path

import pymupdf


def parse_pdf(file_path: Path) -> list[dict]:
    """Return one dict per page: {"page": 1-based number, "text": raw text}."""
    pages = []
    with pymupdf.open(file_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text()
            if text.strip():  # skip empty pages (title images, blank slides)
                pages.append({"page": page_number, "text": text})
    return pages
