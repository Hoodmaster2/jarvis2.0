import logging
import time
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class SemanticSearch:
    def __init__(self, embed_fn: Callable = None):
        self.embed_fn = embed_fn
        self._documents: List[dict] = []
        self._embeddings: List[List[float]] = []

    def set_embed_fn(self, fn: Callable):
        self.embed_fn = fn

    def index_documents(self, documents: List[dict]):
        if not self.embed_fn:
            return
        import asyncio
        for doc in documents:
            try:
                text = doc.get("content", doc.get("path", ""))
                embedding = asyncio.run(self.embed_fn(text))
                if isinstance(embedding, list) and len(embedding) > 0:
                    self._documents.append(doc)
                    self._embeddings.append(embedding)
                else:
                    logger.warning(f"Empty embedding for: {text[:50]}")
            except Exception as e:
                logger.warning(f"Embedding failed for {doc.get('path', 'unknown')}: {e}")
        logger.info(f"Indexed {len(documents)} documents into semantic search")

    def search(self, query: str, k: int = 10) -> List[dict]:
        if not self.embed_fn or not self._documents:
            return []
        import asyncio
        try:
            query_emb = asyncio.run(self.embed_fn(query))
            if not query_emb:
                return []
            scores = []
            for i, doc_emb in enumerate(self._embeddings):
                score = self._cosine_similarity(query_emb, doc_emb)
                scores.append((i, score))
            scores.sort(key=lambda x: x[1], reverse=True)
            top_k = scores[:k]
            results = []
            for idx, score in top_k:
                doc = self._documents[idx].copy()
                doc["score"] = round(score, 4)
                results.append(doc)
            return results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(av * bv for av, bv in zip(a, b))
        norm_a = sum(av * av for av in a) ** 0.5
        norm_b = sum(bv * bv for bv in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def clear(self):
        self._documents.clear()
        self._embeddings.clear()

    def stats(self) -> dict:
        return {"document_count": len(self._documents), "has_embed_fn": self.embed_fn is not None}
