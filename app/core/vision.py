import logging
from pathlib import Path

import pymupdf

from app.core.llm import ask_claude
from app.core.prompts import VISION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def render_page(pdf_path: Path, page_number: int, dpi: int = 120) -> bytes:
    # Opens one slide and take picture by pixmap convert it to png file. 
    # dpi is for quality of the picture.
    with pymupdf.open(pdf_path) as doc:  # `with` closes the file after rendering
        page = doc[page_number - 1]
        pixmap = page.get_pixmap(dpi=dpi)  # draw the page as pixels
        return pixmap.tobytes("png")  # pixels -> PNG file bytes


def describe_page(image_png: bytes, page_text: str) -> str:
    # Ask the vision model for a searchable description of one slide (formulas as text, diagrams in words).
    user = f"<extracted_text>\n{page_text}\n</extracted_text>\n\nDescribe this slide."
    return ask_claude(VISION_SYSTEM_PROMPT, user, max_tokens=1024, image_png=image_png)


def describe_pages(pdf_path: Path, pages: list[dict]) -> list[dict]:
    # For every page: render it, ask the vision model for a description, append it to the page text.
    # A failed page keeps its original text, so one API error doesn't fail the whole file.
    result = []
    for page in pages:
        try:
            description = describe_page(render_page(pdf_path, page["page"]), page["text"])
        except Exception:
            logger.exception("Vision description failed for page %s", page["page"])
            description = ""  # keep the page, just without a description
        result.append({**page, "text": page["text"] + "\n\n" + description})
    return result