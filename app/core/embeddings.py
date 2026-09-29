from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384  # size of one vector for this model; Qdrant collection must match

# bge models are trained to embed search queries with this prefix (passages get none)
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the model once (first call downloads ~130MB to ~/.cache/huggingface), then reuse it."""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed document chunks. One vector per input text, same order."""
    vectors = get_model().encode(texts, batch_size=32, normalize_embeddings=True)
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a user question (with the bge query prefix)."""
    vector = get_model().encode(QUERY_PREFIX + query, normalize_embeddings=True)
    return vector.tolist()
