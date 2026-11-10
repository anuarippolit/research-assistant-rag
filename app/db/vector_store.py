import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FilterSelector, PointStruct, VectorParams, Filter, MatchValue, FieldCondition, MatchAny
from app.core.embeddings import EMBEDDING_DIM
from app.config import settings

QDRANT_URL = settings.qdrant_url
COLLECTION = settings.collection


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection() -> None:
    # reate the collection once. Size must match the embedding model's vector size.
    client = get_client()
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


def upsert_chunks(source_id: str, filename: str, chunks: list[dict], vectors: list[list[float]]) -> None:
    # Write one point per chunk: id + vector + payload (metadata for citations and filters).
    points = [
        PointStruct(
            # Qdrant ids must be int or UUID -> deterministic UUID from (source, chunk):
            # re-ingesting the same file overwrites its points instead of duplicating them
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{chunk['chunk_index']}")),
            vector=vector,
            payload={
                "source_id": source_id,
                "filename": filename,
                "page": chunk["page"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)  # strict: lengths must match
    ]
    get_client().upsert(collection_name=COLLECTION, points=points)

# Delete all points in vector db with that source id
# 1. use get client to get qdrant client
# 2. use client.delete to delete points from collection COLLECTION
# 3. in delete, indicate collection name and what points to delete
# 4. Use FilterSelector to select points to delete, with a Filter that has a must condition that the key "source_id" matches the value of source_id
def delete_source_chunks(source_id:str) -> None:
    get_client().delete(
        collection_name=COLLECTION,
        points_selector=FilterSelector(filter=Filter(must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]))
    )

def search_chunks(query_vector: list[float], k: int=5, source_ids: list[str] | None = None) -> list[dict]:
    if source_ids == []: 
        return []
    q_filter = Filter(must=[FieldCondition(key="source_id", match=MatchAny(any=source_ids))]) if source_ids else None
    results = get_client().query_points(collection_name=COLLECTION, query=query_vector, limit=k, query_filter=q_filter, with_payload=True)
    return [{**p.payload, "score": p.score} for p in results.points]


def get_source_chunks(source_id: str) -> list[dict]:
    # scroll in pages of 100 (offset = bookmark to the next page) -> filter by source_id -> collect payloads -> sort by chunk_index
    client = get_client()
    results, offset = [], None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]),
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        results.extend(p.payload for p in points)
        if offset is None:
            break

    return sorted(results, key=lambda n: n["chunk_index"])
