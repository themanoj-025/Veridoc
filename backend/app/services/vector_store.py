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
            settings=ChromaSettings(anonymized_telemetry=False),
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

    async def delete_document(self, document_id: str) -> None:
        """Delete all chunks for a document."""
        self.collection.delete(where={"document_id": document_id})

    async def count_documents(self) -> int:
        """Get the total number of chunks in the collection."""
        return self.collection.count()


# Singleton
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
