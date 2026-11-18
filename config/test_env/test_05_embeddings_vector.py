
import numpy as np

print("\n=== SENTENCE TRANSFORMERS ===")
from sentence_transformers import util
import torch

vectors = torch.tensor([
    [1.0, 0.0, 0.0],
    [0.9, 0.1, 0.0],
    [0.0, 1.0, 0.0],
])
similarities = util.cos_sim(vectors[0], vectors)
print("Cosine similarity:", similarities.tolist())
assert similarities[0, 1] > similarities[0, 2]

print("\n=== FAISS ===")
import faiss

data = np.array([
    [1.0, 0.0, 0.0],
    [0.9, 0.1, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
], dtype="float32")

index = faiss.IndexFlatL2(3)
index.add(data)
distances, indices = index.search(
    np.array([[0.95, 0.05, 0.0]], dtype="float32"), 2
)
print("FAISS nearest:", indices.tolist(), distances.tolist())
assert indices[0, 0] == 0

print("\n=== CHROMADB ===")
import chromadb

client = chromadb.EphemeralClient()
collection = client.create_collection(
    name="test_vectors",
    embedding_function=None
)
collection.add(
    ids=["a", "b", "c"],
    embeddings=data[:3].tolist(),
    documents=["pierwszy", "drugi", "trzeci"],
)
result = collection.query(
    query_embeddings=[[0.95, 0.05, 0.0]],
    n_results=2,
)
print("Chroma IDs:", result["ids"])
assert result["ids"][0][0] == "a"

print("\n=== QDRANT ===")
from qdrant_client import QdrantClient, models

qdrant = QdrantClient(":memory:")
qdrant.create_collection(
    collection_name="test_vectors",
    vectors_config=models.VectorParams(
        size=3,
        distance=models.Distance.COSINE,
    ),
)
qdrant.upsert(
    collection_name="test_vectors",
    points=[
        models.PointStruct(id=i, vector=vector.tolist(),
                           payload={"label": label})
        for i, (vector, label) in enumerate(zip(
            data[:3], ["pierwszy", "drugi", "trzeci"]
        ))
    ],
)
hits = qdrant.query_points(
    collection_name="test_vectors",
    query=[0.95, 0.05, 0.0],
    limit=2,
).points
print("Qdrant hits:", [(h.id, h.score) for h in hits])
assert hits[0].id == 0

print("\n=== BM25 ===")
from rank_bm25 import BM25Okapi

corpus = [
    ["python", "machine", "learning"],
    ["python", "data", "science"],
    ["knowledge", "graph", "ontology"],
]
bm25 = BM25Okapi(corpus)
scores = bm25.get_scores(["python", "learning"])
print("BM25 scores:", scores.tolist())
assert int(np.argmax(scores)) == 0

print("\nALL TESTS PASSED")

