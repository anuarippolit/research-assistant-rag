import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.embeddings import EMBEDDING_DIM

QDRANT_URL = "http://localhost:6333"
COLLECTION = "chunks"


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection() -> None:
    """Create the collection once. Size must match the embedding model's vector size."""
    client = get_client()
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


def upsert_chunks(source_id: str, filename: str, chunks: list[dict], vectors: list[list[float]]) -> None:
    """Write one point per chunk: id + vector + payload (metadata for citations and filters)."""
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
