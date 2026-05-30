"""
Vector memory layer for semantic search over agent memories.
Supports ChromaDB and LanceDB backends with fallback to simple in-memory.
"""
import json
import logging
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class VectorMemory:
    """Semantic vector memory for agent context retrieval."""

    def __init__(self, embed_fn, backend: str = "memory", persist_dir: str = "./data/vectors"):
        self._embed = embed_fn
        self.backend = backend
        self.persist_dir = persist_dir
        self._store = None
        self._init_backend()

    def _init_backend(self):
        """Initialize the vector storage backend."""
        if self.backend == "chroma":
            self._init_chroma()
        elif self.backend == "lancedb":
            self._init_lancedb()
        else:
            self._init_in_memory()

    def _init_in_memory(self):
        """Simple in-memory vector store."""
        self._store = InMemoryVectorStore(self._embed)
        logger.info("Using in-memory vector store")

    def _init_chroma(self):
        """Initialize ChromaDB backend."""
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(
                name="jarvis_memories",
                metadata={"hnsw:space": "cosine"},
            )
            self._store = ChromaDBStore(self._collection, self._embed)
            logger.info("Using ChromaDB vector store")
        except ImportError:
            logger.warning("ChromaDB not installed, falling back to in-memory")
            self.backend = "memory"
            self._init_in_memory()

    def _init_lancedb(self):
        """Initialize LanceDB backend."""
        try:
            import lancedb
            import pyarrow as pa
            self._db = lancedb.connect(self.persist_dir)
            self._store = LanceDBStore(self._db, self._embed)
            logger.info("Using LanceDB vector store")
        except ImportError:
            logger.warning("LanceDB not installed, falling back to in-memory")
            self.backend = "memory"
            self._init_in_memory()

    def add(self, text: str, metadata: dict = None, namespace: str = "default") -> str:
        """Add a text entry to vector memory."""
        return self._store.add(text, metadata or {}, namespace)

    def search(self, query: str, k: int = 5, namespace: str = None) -> list[dict]:
        """Semantic search over stored memories."""
        return self._store.search(query, k, namespace)

    def delete(self, doc_id: str):
        """Delete a document by ID."""
        self._store.delete(doc_id)

    def clear(self, namespace: str = None):
        """Clear all vectors or a namespace."""
        self._store.clear(namespace)

    def get_stats(self) -> dict:
        return self._store.get_stats()


# --- In-Memory Implementation ---

class InMemoryVectorStore:
    """Simple in-memory vector store using cosine similarity."""

    def __init__(self, embed_fn):
        self._embed = embed_fn
        self._docs: dict[str, dict] = {}
        self._vectors: dict[str, list[float]] = {}
        self._namespaces: dict[str, set] = {}

    def add(self, text: str, metadata: dict, namespace: str) -> str:
        doc_id = str(uuid.uuid4())
        vector = self._embed(text)
        if not vector or len(vector) == 0:
            vector = [0.0] * 768
        self._docs[doc_id] = {"text": text, "metadata": metadata, "namespace": namespace, "created_at": time.time()}
        self._vectors[doc_id] = vector
        if namespace not in self._namespaces:
            self._namespaces[namespace] = set()
        self._namespaces[namespace].add(doc_id)
        return doc_id

    def search(self, query: str, k: int, namespace: str = None) -> list[dict]:
        if not self._docs:
            return []
        query_vec = self._embed(query)
        if not query_vec or len(query_vec) == 0:
            return []

        import math

        def cosine_sim(a, b):
            dot = sum(ai * bi for ai, bi in zip(a, b))
            na = math.sqrt(sum(ai * ai for ai in a))
            nb = math.sqrt(sum(bi * bi for bi in b))
            return dot / (na * nb + 1e-10)

        scored = []
        for doc_id, vec in self._vectors.items():
            if namespace and self._docs[doc_id].get("namespace") != namespace:
                continue
            sim = cosine_sim(query_vec, vec)
            scored.append((sim, doc_id))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, doc_id in scored[:k]:
            doc = dict(self._docs[doc_id])
            doc["id"] = doc_id
            doc["score"] = sim
            results.append(doc)
        return results

    def delete(self, doc_id: str):
        if doc_id in self._docs:
            ns = self._docs[doc_id].get("namespace")
            if ns and ns in self._namespaces:
                self._namespaces[ns].discard(doc_id)
            del self._docs[doc_id]
            self._vectors.pop(doc_id, None)

    def clear(self, namespace: str = None):
        if namespace:
            for doc_id in list(self._namespaces.get(namespace, set())):
                self.delete(doc_id)
        else:
            self._docs.clear()
            self._vectors.clear()
            self._namespaces.clear()

    def get_stats(self) -> dict:
        ns_counts = {ns: len(ids) for ns, ids in self._namespaces.items()}
        return {"total_docs": len(self._docs), "namespaces": ns_counts, "backend": "memory"}


# --- ChromaDB Implementation ---

class ChromaDBStore:
    def __init__(self, collection, embed_fn):
        self._collection = collection
        self._embed = embed_fn

    def add(self, text: str, metadata: dict, namespace: str) -> str:
        doc_id = str(uuid.uuid4())
        vec = self._embed(text)
        if not vec:
            vec = [0.0] * 768
        md = dict(metadata)
        md["namespace"] = namespace
        md["text"] = text
        self._collection.add(ids=[doc_id], embeddings=[vec], metadatas=[md])
        return doc_id

    def search(self, query: str, k: int, namespace: str = None) -> list[dict]:
        query_vec = self._embed(query)
        if not query_vec:
            return []
        filter_expr = {"namespace": namespace} if namespace else None
        results = self._collection.query(
            query_embeddings=[query_vec],
            n_results=k,
            where=filter_expr,
        )
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "text": results["metadatas"][0][i].get("text", ""),
                "metadata": {k: v for k, v in results["metadatas"][0][i].items() if k != "text"},
                "score": results["distances"][0][i] if results.get("distances") else 0,
            })
        return docs

    def delete(self, doc_id: str):
        self._collection.delete(ids=[doc_id])

    def clear(self, namespace: str = None):
        if namespace:
            all_docs = self._collection.get()
            to_delete = [
                all_docs["ids"][i]
                for i in range(len(all_docs["ids"]))
                if all_docs["metadatas"][i].get("namespace") == namespace
            ]
            if to_delete:
                self._collection.delete(ids=to_delete)
        else:
            self._collection.delete(ids=self._collection.get()["ids"])

    def get_stats(self) -> dict:
        count = self._collection.count()
        return {"total_docs": count, "backend": "chroma"}


# --- LanceDB Implementation ---

class LanceDBStore:
    def __init__(self, db, embed_fn):
        self._db = db
        self._embed = embed_fn
        self._table_name = "jarvis_memories"
        self._init_table()

    def _init_table(self):
        try:
            self._table = self._db.open_table(self._table_name)
        except Exception:
            import pyarrow as pa
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.string()),
                pa.field("namespace", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
                pa.field("created_at", pa.float64()),
            ])
            self._table = self._db.create_table(self._table_name, schema=schema, mode="overwrite")

    def add(self, text: str, metadata: dict, namespace: str) -> str:
        import pyarrow as pa
        doc_id = str(uuid.uuid4())
        vec = self._embed(text)
        if not vec:
            vec = [0.0] * 768
        data = pa.table({
            "id": [doc_id],
            "text": [text],
            "metadata": [json.dumps(metadata)],
            "namespace": [namespace],
            "vector": [vec],
            "created_at": [time.time()],
        })
        self._table.add(data)
        return doc_id

    def search(self, query: str, k: int, namespace: str = None) -> list[dict]:
        query_vec = self._embed(query)
        if not query_vec:
            return []
        try:
            results = self._table.search(query_vec).limit(k).to_pandas()
            docs = []
            for _, row in results.iterrows():
                if namespace and row.get("namespace") != namespace:
                    continue
                docs.append({
                    "id": row.get("id"),
                    "text": row.get("text", ""),
                    "metadata": json.loads(row.get("metadata", "{}")),
                    "score": float(row.get("_distance", 0)),
                })
            return docs
        except Exception as e:
            logger.error(f"LanceDB search error: {e}")
            return []

    def delete(self, doc_id: str):
        try:
            self._table.delete(f"id = '{doc_id}'")
        except Exception as e:
            logger.error(f"LanceDB delete error: {e}")

    def clear(self, namespace: str = None):
        try:
            if namespace:
                self._table.delete(f"namespace = '{namespace}'")
            else:
                self._db.drop_table(self._table_name)
                self._init_table()
        except Exception as e:
            logger.error(f"LanceDB clear error: {e}")

    def get_stats(self) -> dict:
        try:
            count = len(self._table.to_pandas())
            return {"total_docs": count, "backend": "lancedb"}
        except Exception:
            return {"total_docs": 0, "backend": "lancedb"}
