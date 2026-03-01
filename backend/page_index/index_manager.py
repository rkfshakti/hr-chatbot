"""
Embedding-based resume index.
Replaces PageIndex with a simple local vector store backed by
text-embedding-mxbai-embed-large-v1 (served at 192.168.68.113:1234).
"""
import json
import logging
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional numpy for faster cosine similarity (pure-python fallback included)
# ---------------------------------------------------------------------------
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    if _HAS_NUMPY:
        va, vb = np.array(a), np.array(b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        return float(np.dot(va, vb) / denom) if denom else 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if (norm_a and norm_b) else 0.0


class PageIndexManager:
    """
    Embedding-based vector store for resumes.

    Stores embeddings in memory and persists them to
    `{db_path}/resume_store.json` so they survive restarts.

    Embedding model: text-embedding-mxbai-embed-large-v1 (1024-dim)
    """

    def __init__(self, index_name: str = "resumes", db_path: str = "./data/pageindex"):
        self.index_name = index_name
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        self._store_path = os.path.join(db_path, "resume_store.json")

        # In-memory store: { resume_id: {text, metadata, embedding} }
        self._store: Dict[str, Dict[str, Any]] = {}
        self._load_store()

        # Lazy-init embedding client (avoids circular import at startup)
        self._embed_client = None
        logger.info(
            f"EmbeddingIndexManager ready — "
            f"{len(self._store)} resumes loaded from {self._store_path}"
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_store(self):
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "r") as f:
                    self._store = json.load(f)
                logger.info(f"Loaded {len(self._store)} resumes from disk.")
            except Exception as e:
                logger.warning(f"Could not load store: {e} — starting fresh.")
                self._store = {}

    def _save_store(self):
        try:
            with open(self._store_path, "w") as f:
                json.dump(self._store, f)
        except Exception as e:
            logger.error(f"Could not save store: {e}")

    # ------------------------------------------------------------------
    # Embedding helper
    # ------------------------------------------------------------------

    def _get_embed_client(self):
        if self._embed_client is None:
            from models.llm_client import EmbeddingClient
            self._embed_client = EmbeddingClient()
        return self._embed_client

    async def _embed(self, text: str) -> Optional[List[float]]:
        try:
            return await self._get_embed_client().embed(text)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def add_resume(
        self,
        resume_id: str,
        candidate_name: str,
        raw_text: str,
        metadata: Dict[str, Any],
        source_file: str,
    ) -> bool:
        """Embed and store a resume."""
        embedding = await self._embed(raw_text)
        entry: Dict[str, Any] = {
            "id": resume_id,
            "content": raw_text,
            "metadata": {
                "candidate_name": candidate_name,
                "source_file": source_file,
                "uploaded_date": datetime.now().isoformat(),
                **metadata,
            },
            "embedding": embedding or [],
        }
        self._store[resume_id] = entry
        self._save_store()
        if embedding:
            logger.info(f"Stored resume with embedding: {resume_id} ({candidate_name})")
        else:
            logger.warning(f"Stored resume WITHOUT embedding: {resume_id} ({candidate_name})")
        return True

    async def search_resumes(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over stored resumes using cosine similarity.
        Falls back to keyword search if no embeddings are stored.
        """
        if not self._store:
            return []

        q_emb = await self._embed(query)
        if q_emb:
            scored = []
            for rid, entry in self._store.items():
                stored_emb = entry.get("embedding")
                if stored_emb:
                    score = _cosine_similarity(q_emb, stored_emb)
                    scored.append((score, entry))
            if scored:
                scored.sort(key=lambda x: x[0], reverse=True)
                return [
                    {**e, "score": round(s, 4)}
                    for s, e in scored[:top_k]
                ]

        # Keyword fallback
        logger.warning("Falling back to keyword search (no embeddings available).")
        query_lower = query.lower()
        results = []
        words = query_lower.split()
        for entry in self._store.values():
            text = entry.get("content", "").lower()
            hits = sum(1 for w in words if w in text)
            if hits:
                results.append({**entry, "score": hits / len(words)})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_resume_by_id(self, resume_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(resume_id)

    def list_all_resumes(self) -> List[Dict[str, Any]]:
        return list(self._store.values())

    def delete_resume(self, resume_id: str) -> bool:
        if resume_id in self._store:
            del self._store[resume_id]
            self._save_store()
            logger.info(f"Deleted resume: {resume_id}")
            return True
        return False

    async def search_by_skills(
        self, skills: List[str], top_k: int = 10
    ) -> List[Dict[str, Any]]:
        return await self.search_resumes(query=" ".join(skills), top_k=top_k)

    async def search_by_experience(
        self,
        min_years: int,
        max_years: Optional[int] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        return await self.search_resumes(
            query=f"{min_years}+ years experience", top_k=top_k
        )

    async def bulk_add_resumes(self, resumes: List[Dict[str, Any]]) -> int:
        count = 0
        for r in resumes:
            ok = await self.add_resume(
                resume_id=r.get("id", ""),
                candidate_name=r.get("metadata", {}).get("candidate_name", "Unknown"),
                raw_text=r.get("content", ""),
                metadata=r.get("metadata", {}),
                source_file=r.get("metadata", {}).get("source_file", ""),
            )
            if ok:
                count += 1
        return count
