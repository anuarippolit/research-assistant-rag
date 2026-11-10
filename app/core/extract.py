from app.db.vector_store import search_chunks
from app.core.embeddings import embed_query
from app.schemas import Cell
from app.core.prompts import build_extract_prompt
from app.core.llm import ask_claude
from pydantic import ValidationError
import logging
from app.db.sqlite import get_source, list_sources

logger = logging.getLogger(__name__)

# the answer is ~60 tokens; the rest is headroom for the model's thinking tokens, which also count
EXTRACT_MAX_TOKENS = 1500


def extract_feature(source_id: str, feature: str) -> Cell:
    # embed feature -> search_chunks in one source -> build_extract_prompt -> ask_claude -> parse JSON into Cell
    chunks = search_chunks(embed_query(feature), k=5, source_ids=[source_id])
    if not chunks:
        return Cell()
    system, user = build_extract_prompt(feature, chunks)
    raw = None
    try:
        raw = ask_claude(system, user, max_tokens=EXTRACT_MAX_TOKENS)
        return Cell.model_validate_json(raw)
    except ValidationError:
        logger.warning("Bad JSON for %s: %r", feature, raw)
    except Exception:  # API error: one failed cell must not kill the whole table
        logger.exception("Extract failed for source %s, feature %s", source_id, feature)
    return Cell()


def extract_table(source_ids: list[str] | None, features: list[str]) -> dict:
    # None -> every ready source; per source and feature one extract_feature call -> table rows
    if source_ids is None:
        source_ids = [s["id"] for s in list_sources() if s["status"] == "ready"]
    if not source_ids:
        raise ValueError("No sources to extract from")

    rows = []
    for source_id in source_ids:
        source = get_source(source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")
        cells = {f: extract_feature(source_id, f) for f in features}
        rows.append({"source": source["filename"], "cells": cells})
    return {"features": features, "rows": rows}
