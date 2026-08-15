"""Dense vector search — semantic retrieval using sentence-transformers embeddings."""

from __future__ import annotations

import structlog

from app.services.ingestion import get_embedding_model
from app.services.vector_store import get_vector_store

logger = structlog.get_logger(__name__)


async def dense_search(
    query: str,
    document_ids: list[str] | None = None,
    top_k: int = 20,
) -> list[dict]:
    """Search chunks using dense vector embeddings."""
    model = get_embedding_model()
    query_embedding = model.encode(query).tolist()

    vs = get_vector_store()
    results = await vs.search(
        query_embedding=query_embedding,
        document_ids=document_ids,
        top_k=top_k,
    )

    return results
