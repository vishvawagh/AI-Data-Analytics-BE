
import numpy as np
from app.rag.embeddings import get_embedding
from app.rag.vectorstore import index, schema_chunks

def retrieve_schema(query: str, top_k=2):
    query_vec = np.array([get_embedding(query)])

    distances, indices = index.search(query_vec, top_k)

    results = [schema_chunks[i] for i in indices[0]]

    return "\n".join(results)