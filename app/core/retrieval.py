from app.db.vector_store import COLLECTION, get_client
from app.core.embeddings import EMBEDDING_DIM, embed_query
import numpy as np

# Load all chunks from the vector store and return them as a matrix and a list of payloads.
# 1. Initialize an empty list to store all points and set the offset to None.
# 2. Get the client for the vector store.
# 3. Scroll through the collection in batches of 100 points, retrieving both the vectors (with_vectors=True) and their associated payloads (with_payload=True)
# 4. Break loop when no next offset
# 5. If no points were retrieved, return an empty matrix and an empty list.
# 6. converting th elist into numpy array using np.array([p.vector for p in all_points])
def load_all_chunks() -> tuple[np.ndarray, list[dict]]:
    all_points, offset = [], None
    client = get_client()
    while True:
        points, offset = client.scroll(collection_name=COLLECTION, limit=100, offset=offset, with_payload=True, with_vectors=True)
        all_points.extend(points)
        if offset is None:
            break

    if not all_points:
        return np.empty((0, EMBEDDING_DIM)), []

    matrix = np.array([p.vector for p in all_points])
    payloads = [p.payload for p in all_points]
    return matrix, payloads

# tok k similliarity -> using dot product 
# load all chunks @ embed query (that wrapped into np.array(), since embed_qury returns a list) = scores (similliarity)
# get top k using argsort -> [start:end:step=-1 -> go from end to start] -> [:k] -> взять первые k
# return list of dict with payloads and score
# **  unpack dict inside another dict, so we basically add scores field to the payload dict
def search_numpy(query: str, k: int = 5) -> list[dict]:
    matrix, payloads = load_all_chunks()
    q = np.array(embed_query(query))
    scores = matrix @ q
    top_k = np.argsort(scores)[::-1][:k]
    return [ {**payloads[i], "score": float(scores[i])} for i in top_k]
