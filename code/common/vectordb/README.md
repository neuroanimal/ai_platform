# Vector Database Support

Vector database adapters for AI Platform.

## Supported Databases

- **ChromaDB**: Open-source embedding database
- **FAISS**: Facebook AI Similarity Search
- **Qdrant**: Vector similarity search engine
- **PGVector**: PostgreSQL vector extension
- **SQLite**: Via libSQL/Turso
- **Elasticsearch**: Search and analytics engine
- **OpenSearch**: Community-driven search
- **Weaviate**: Vector search engine
- **Milvus**: Cloud-native vector database
- **Pinecone**: Managed vector database
- **Lantern**: PostgreSQL vector extension
- **TXTai**: Semantic search
- **LanceDB**: Serverless vector database

## Usage

```python
from code.common.vectordb.vectordb_registry import get_registry
from code.common.vectordb.chromadb_adapter import ChromaDBAdapter

registry = get_registry()
registry.register("chromadb", ChromaDBAdapter)

db = registry.get("chromadb")
db.connect({"host": "localhost"})
db.insert([[0.1, 0.2]], [{"id": 1}])
results = db.search([0.1, 0.2], top_k=5)
db.disconnect()
```
