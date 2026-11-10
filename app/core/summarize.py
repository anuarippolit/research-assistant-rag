from app.core.llm import ask_claude
from app.core.prompts import build_combined_prompt, build_summary_prompt
from app.db.sqlite import get_source, get_summary, list_sources, save_summary
from app.db.vector_store import get_source_chunks

# a summary is ~600 tokens; the rest is headroom for the model's thinking tokens, which also count
SUMMARY_MAX_TOKENS = 3000


def summarize_source(source_id: str, refresh: bool = False) -> str:
    # get_summary (cache hit? return) -> get_source_chunks -> build_summary_prompt -> ask_claude -> save_summary
    cached = get_summary(source_id)
    if cached is not None and not refresh:
        return cached

    chunks = get_source_chunks(source_id)
    if not chunks:
        # not ready yet, failed, or empty: the API layer turns this into an HTTP error
        raise ValueError(f"Source {source_id} has no chunks (not ready or failed)")

    system, user = build_summary_prompt(chunks)
    text = ask_claude(system, user, max_tokens=SUMMARY_MAX_TOKENS)
    save_summary(source_id, text)
    return text


def summarize_all(source_ids: list[str] | None = None, refresh: bool = False) -> str:
    # None -> every ready source; each summarize_source (cached) -> one combine call over the summaries
    if source_ids is None:
        source_ids = [s["id"] for s in list_sources() if s["status"] == "ready"]
    if not source_ids:  # also covers an explicit []: "search in zero sources" is not "everything"
        raise ValueError("No sources to summarize")

    summaries = []  # [(filename, summary_text), ...]
    for source_id in source_ids:
        source = get_source(source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")
        summaries.append((source["filename"], summarize_source(source_id, refresh)))

    if len(summaries) == 1:
        return summaries[0][1]  # nothing to combine, skip the extra Claude call

    system, user = build_combined_prompt(summaries)
    return ask_claude(system, user, max_tokens=SUMMARY_MAX_TOKENS)
