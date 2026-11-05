from app.core.embeddings import embed_query
from app.db.vector_store import search_chunks
from app.core.prompts import build_chat_prompt, NOT_FOUND_MESSAGE
from app.core.llm import ask_claude

def answer(question: str, source_ids: list[str] | None = None, k: int=5) -> dict:
    # Embed query and get chunks from vector database
    query_vector = embed_query(question)
    chunks = search_chunks(query_vector, source_ids=source_ids, k=k)
    if not chunks:
        return {"answer": NOT_FOUND_MESSAGE, "sources": []}

    # Build prompt and ask Claude
    system, user = build_chat_prompt(question, chunks)
    text = ask_claude(system, user)
    return {"answer": text, "sources": [{ "filename": c["filename"], "page": c["page"], "score": c["score"] } for c in chunks]}

