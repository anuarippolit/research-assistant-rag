import logging
from pathlib import Path

from app.core.chunking import chunk_pages
from app.core.embeddings import embed_texts
from app.core.parsing import parse_pdf
from app.db.sqlite import update_source_status
from app.db.vector_store import upsert_chunks

logger = logging.getLogger(__name__)


def ingest_source(source_id: str, filename: str, file_path: Path) -> None:
    """Full pipeline for one uploaded file: parse -> chunk -> embed -> upsert.
    Runs in the background, so it never raises: the outcome goes to sources.status.
    """
    update_source_status(source_id, "processing")
    try:
        pages = parse_pdf(file_path)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No extractable text (scanned/image-only PDF? OCR is not supported)")

        vectors = embed_texts([chunk["text"] for chunk in chunks])
        upsert_chunks(source_id, filename, chunks, vectors)

        update_source_status(source_id, "ready")
        logger.info("Ingested %s: %d pages, %d chunks", filename, len(pages), len(chunks))
    except Exception as e:
        # nobody is waiting for this function's result, so record the error instead of raising
        logger.exception("Ingestion failed for %s", filename)
        update_source_status(source_id, "failed", error=str(e))
