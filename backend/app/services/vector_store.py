"""Vector store — ChromaDB wrapper for document embeddings."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.config import settings


class VectorStore:
    """Wrapper around ChromaDB for document embeddings."""

    def __init__(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                chroma_server_grpc_max_message_length=settings.chroma_timeout * 1000 * 1000,
            ),
        )
        # Apply HTTP timeout — the underlying httpx client respects this
        # by setting a read timeout on the transport adapter
        import httpx
        transport = httpx.AsyncHTTPTransport(retries=1)
        self.client._client = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(settings.chroma_timeout),
            follow_redirects=True,
        )
        self.collection_name = settings.chroma_collection
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(self.collection_name)
            except ValueError:
                self._collection = self.client.create_collection(
                    self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        return self._collection

    async def add_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> list[str]:
        """Add chunks with embeddings to the vector store."""
        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [
            {
                "document_id": c["document_id"],
                "chunk_index": c.get("chunk_index", 0),
                "page_number": c.get("page_number"),
                "document_title": c.get("document_title", ""),
            }
            for c in chunks
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return ids

    async def search(
        self,
        query_embedding: list[float],
        document_ids: list[str] | None = None,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks by embedding."""
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                chunks.append({
                    "chunk_id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "document_id": results["metadatas"][0][i].get("document_id", ""),
                    "document_title": results["metadatas"][0][i].get("document_title", ""),
                    "page_number": results["metadatas"][0][i].get("page_number"),
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
                    "source": "vector",
                })
        return chunks

    async def get_all_chunks(self, document_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Retrieve ALL chunks for the given document IDs (not just top-k).

        Used by the BM25 indexer to build a complete lexical index over
        the full document corpus, rather than only the top dense results.
        """
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}

        results = self.collection.get(
            where=where,
            include=["documents", "metadatas"],
        )

        chunks: list[dict[str, Any]] = []
        if results["ids"]:
            for i in range(len(results["ids"])):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                chunks.append({
                    "chunk_id": results["ids"][i],
                    "content": results["documents"][i] if results["documents"] else "",
                    "document_id": meta.get("document_id", ""),
                    "document_title": meta.get("document_title", ""),
                    "page_number": meta.get("page_number"),
                })
        return chunks

    async def delete_document(self, document_id: str) -> None:
        """Delete all chunks for a document."""
        self.collection.delete(where={"document_id": document_id})

        # Invalidate BM25 cache when documents are deleted
        # (lazy import avoids circular dep: vector_store → retrieval.bm25 → retrieval.dense → vector_store)
        from app.services.retrieval.bm25 import invalidate_bm25_index as _invalidate  # type: ignore[import]
        _invalidate()

    async def count_documents(self) -> int:
        """Get the total number of chunks in the collection."""
        return self.collection.count()


def get_vector_store() -> VectorStore:
    """Get the VectorStore instance.

    Checks the DI container first (see :class:`app.core.di.DIContainer`).
    Falls back to an uncached instance when no container is active
    (standalone scripts, some test scenarios).
    """
    from app.core.di import get_di_container

    container = get_di_container()
    if container is not None:
        return container.get_or_create_vector_store()
    return VectorStore()
