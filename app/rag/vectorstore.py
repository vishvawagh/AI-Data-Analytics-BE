
import faiss
import numpy as np
from app.rag.embeddings import get_embedding

schema_chunks = [
    "products table: product_id, product_name, category_id, launch_date, price",
    "sales table: sale_id, sale_date, store_id, product_id, quantity",
    "stores table: store_id, store_name, city, country",
    "category table: category_id, category_name",
    "warranty table: claim_id, claim_date, sale_id, repair_status"
]

# Create embeddings
embeddings = [get_embedding(text) for text in schema_chunks]
dimension = len(embeddings[0])

index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))