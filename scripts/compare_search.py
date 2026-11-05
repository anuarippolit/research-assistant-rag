import math

from app.core.embeddings import embed_query
from app.core.retrieval import search_numpy
from app.db.vector_store import search_chunks

# get the address of the chunk
def key(r: dict) -> tuple:
    return (r["filename"], r["page"], r["chunk_index"])


def compare_search(query: str, k: int = 5) -> None:
    qdrant_results = search_chunks(embed_query(query), k=k)
    numpy_results = search_numpy(query, k=k)

    # check the order of the results and that scores are the same. 
    same_order = [key(r) for r in qdrant_results] == [key(r) for r in numpy_results]
    same_scores = all(
        math.isclose(q["score"], n["score"], abs_tol=1e-6)
        for q, n in zip(qdrant_results, numpy_results)  
    )

    print(f"{query!r} | order: {same_order} | scores: {same_scores}")


if __name__ == "__main__":  
    compare_search("what is logistic regression?")
    compare_search("what is a multilayer perceptron?")
