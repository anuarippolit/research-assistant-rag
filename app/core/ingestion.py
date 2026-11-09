import logging
from pathlib import Path

from app.core.chunking import chunk_pages, drop_build_steps
from app.core.embeddings import embed_texts
from app.core.parsing import parse_pdf
from app.core.vision import describe_pages
from app.db.sqlite import update_source_status
from app.db.vector_store import upsert_chunks

logger = logging.getLogger(__name__)


def ingest_source(source_id: str, filename: str, file_path: Path) -> None:
    # Full pipeline --- parse -> drop duplicate slides -> describe (vision) -> chunk -> embed -> upsert
    # Runs in the background, so it never raises: the outcome goes to sources.status.

    update_source_status(source_id, "processing")
    try:
        pages = parse_pdf(file_path)
        total_pages = len(pages)
        pages = drop_build_steps(pages)
        pages = describe_pages(file_path, pages)  # page text + vision description of the slide
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No extractable text (scanned/image-only PDF? OCR is not supported)")

        vectors = embed_texts([chunk["text"] for chunk in chunks])
        upsert_chunks(source_id, filename, chunks, vectors)

        update_source_status(source_id, "ready")
        logger.info(
            "Ingested %s: %d pages described by vision (%d build steps dropped), %d chunks",
            filename, len(pages), total_pages - len(pages), len(chunks),
        )
    except Exception as e:
        # nobody is waiting for this function's result, so record the error instead of raising
        logger.exception("Ingestion failed for %s", filename)
        update_source_status(source_id, "failed", error=str(e))
