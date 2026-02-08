"""Example usage of vector database adapters."""

from code.common.vectordb.vectordb_registry import get_registry
from code.common.vectordb.chromadb_adapter import ChromaDBAdapter
from code.common.vectordb.faiss_adapter import FAISSAdapter
from code.common.vectordb.qdrant_adapter import QdrantAdapter
from code.common.vectordb.pgvector_adapter import PGVectorAdapter
from code.common.vectordb.sqlite_adapter import SQLiteAdapter
from code.common.vectordb.elasticsearch_adapter import ElasticsearchAdapter
from code.common.vectordb.opensearch_adapter import OpenSearchAdapter
from code.common.vectordb.weaviate_adapter import WeaviateAdapter
from code.common.vectordb.milvus_adapter import MilvusAdapter
from code.common.vectordb.pinecone_adapter import PineconeAdapter
from code.common.vectordb.lantern_adapter import LanternAdapter
from code.common.vectordb.txtai_adapter import TXTaiAdapter
from code.common.vectordb.lancedb_adapter import LanceDBAdapter

def main():
    """Register and test all vector database adapters."""
    registry = get_registry()

    dbs = {
        "chromadb": ChromaDBAdapter,
        "faiss": FAISSAdapter,
        "qdrant": QdrantAdapter,
        "pgvector": PGVectorAdapter,
        "sqlite": SQLiteAdapter,
        "elasticsearch": ElasticsearchAdapter,
        "opensearch": OpenSearchAdapter,
        "weaviate": WeaviateAdapter,
        "milvus": MilvusAdapter,
        "pinecone": PineconeAdapter,
        "lantern": LanternAdapter,
        "txtai": TXTaiAdapter,
        "lancedb": LanceDBAdapter,
    }

    for name, adapter_class in dbs.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(dbs)} vector databases: {registry.list()}\n")

    for name in dbs:
        adapter = registry.get(name)
        adapter.connect({})
        result = adapter.search([0.1, 0.2, 0.3], top_k=5)
        print(f"{result[0]['db']}: OK")
        adapter.disconnect()

if __name__ == "__main__":
    main()
