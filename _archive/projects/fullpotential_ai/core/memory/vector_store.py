"""
ChromaDB-backed semantic memory utilities.

This module centralizes semantic storage for activities/episodes so that
any service can log new context and recall it later by meaning.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

_logger = logging.getLogger(__name__)

try:
    import chromadb  # type: ignore
except Exception as exc:  # pragma: no cover - best-effort import
    chromadb = None  # type: ignore
    _CHROMA_IMPORT_ERROR = exc  # type: ignore
else:
    _CHROMA_IMPORT_ERROR = None

try:
    from openai import OpenAI  # type: ignore
except Exception as exc:  # pragma: no cover - best-effort import
    OpenAI = None  # type: ignore
    _OPENAI_IMPORT_ERROR = exc  # type: ignore
else:
    _OPENAI_IMPORT_ERROR = None

EMBEDDING_DIM = 1536  # Matches text-embedding-3-small
_CLIENT_LOCK = threading.Lock()
_CLIENT: Optional["SemanticVectorStore"] = None


def _hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Deterministic embedding fallback when OpenAI is unavailable.
    """
    vec = [0.0] * dim
    if not text:
        return vec

    for token in text.lower().split():
        idx = hash(token) % dim
        vec[idx] += 1.0

    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _normalize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ensure metadata conforms to Chroma's primitive constraints.
    """
    if not metadata:
        return {}

    normalized: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        elif isinstance(value, (list, tuple, set)):
            normalized[key] = ", ".join(str(v) for v in value)
        else:
            try:
                normalized[key] = json.dumps(value)
            except Exception:
                normalized[key] = str(value)
    return normalized


@dataclass
class RecallResult:
    episode_id: str
    score: float
    document: str
    metadata: Dict[str, Any]


class SemanticVectorStore:
    """
    Thin wrapper around ChromaDB with OpenAI embeddings + deterministic fallback.
    """

    def __init__(
        self,
        persist_path: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        if chromadb is None:  # pragma: no cover
            raise RuntimeError(
                "chromadb is not installed. Please `pip install chromadb`."
            ) from _CHROMA_IMPORT_ERROR

        self.persist_path = Path(
            persist_path
            or os.getenv("FPAI_VECTOR_STORE_PATH", "/opt/fpai/core/memory/chroma_db")
        )
        self.persist_path.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(path=str(self.persist_path))
        collection = client.get_or_create_collection(
            name=collection_name or os.getenv("FPAI_VECTOR_COLLECTION", "fpai_episodes"),
            metadata={"hnsw:space": os.getenv("FPAI_VECTOR_DISTANCE", "cosine")},
        )

        self._client = client
        self._collection = collection
        self._openai_client: Optional[Any] = None
        self._embed_model = os.getenv("FPAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # --- Private helpers -------------------------------------------------

    def _get_openai_client(self) -> Optional[Any]:
        if self._openai_client is not None:
            return self._openai_client

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or OpenAI is None:
            return None

        self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    def _embed(self, text: str) -> List[float]:
        text = (text or "").strip()
        if not text:
            return _hash_embedding(text)

        client = self._get_openai_client()
        if not client:
            return _hash_embedding(text)

        try:
            response = client.embeddings.create(
                model=self._embed_model,
                input=text,
            )
            vector = response.data[0].embedding
            return [float(v) for v in vector]
        except Exception as exc:  # pragma: no cover - network errors
            _logger.debug("OpenAI embedding failed, using hash fallback: %s", exc)
            return _hash_embedding(text)

    # --- Public API ------------------------------------------------------

    def add_episode(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Embed and store an episode document. Returns the stored episode_id.
        """
        episode_id = (
            metadata.get("episode_id")
            if metadata and metadata.get("episode_id")
            else f"ep-{uuid.uuid4().hex}"
        )
        normalized_meta = _normalize_metadata({**(metadata or {}), "episode_id": episode_id})
        embedding = self._embed(text)

        self._collection.upsert(
            ids=[episode_id],
            documents=[text],
            metadatas=[normalized_meta],
            embeddings=[embedding],
        )

        return episode_id

    def recall(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RecallResult]:
        """
        Recall semantically similar episodes ordered by cosine similarity.
        """
        limit = max(1, limit)
        query_vector = self._embed(query)

        where_clause = filters or None
        result = self._collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where_clause or None,
            include=["documents", "metadatas", "distances"],
        )

        hits: List[RecallResult] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        dists = result.get("distances", [[]])[0]
        metas = result.get("metadatas", [[]])[0]

        for idx, episode_id in enumerate(ids):
            distance = float(dists[idx]) if idx < len(dists) else 0.0
            # Convert cosine distance to similarity score
            score = max(0.0, 1.0 - distance)
            doc = docs[idx] if idx < len(docs) else ""
            meta = metas[idx] if idx < len(metas) else {}
            hits.append(
                RecallResult(
                    episode_id=str(episode_id),
                    score=score,
                    document=str(doc),
                    metadata=meta or {},
                )
            )

        return hits


def get_client() -> Optional[SemanticVectorStore]:
    """
    Lazy singleton accessor for the semantic vector store.
    """
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    with _CLIENT_LOCK:
        if _CLIENT is not None:
            return _CLIENT
        try:
            _CLIENT = SemanticVectorStore()
        except Exception as exc:  # pragma: no cover
            _logger.warning("Semantic vector store unavailable: %s", exc)
            return None
    return _CLIENT


def add_episode(text: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Best-effort helper to add an episode to the global vector store.
    """
    client = get_client()
    if not client:
        return None
    try:
        return client.add_episode(text=text, metadata=metadata)
    except Exception as exc:  # pragma: no cover
        _logger.warning("Failed to add episode to vector store: %s", exc)
        return None


def recall(
    query: str,
    limit: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> List[RecallResult]:
    """
    Helper that recalls semantic memories without exposing the client.
    """
    client = get_client()
    if not client:
        return []
    try:
        return client.recall(query=query, limit=limit, filters=filters)
    except Exception as exc:  # pragma: no cover
        _logger.warning("Vector recall failed: %s", exc)
        return []


