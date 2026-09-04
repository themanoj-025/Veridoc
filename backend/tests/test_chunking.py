"""Tests for Veridoc text chunking service."""


import pytest

from app.services.chunking import recursive_chunk_text

pytestmark = pytest.mark.unit

class TestRecursiveChunkText:
    """Tests for recursive boundary-aware text chunking."""

    def test_empty_text(self) -> None:
        chunks = recursive_chunk_text("", "doc1", "Test Doc")
        assert chunks == []

    def test_short_text_single_chunk(self) -> None:
        text = "This is a short document."
        chunks = recursive_chunk_text(text, "doc1", "Test")
        assert len(chunks) == 1
        assert chunks[0]["content"] == text

    def test_paragraph_splitting(self) -> None:
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = recursive_chunk_text(text, "doc1", "Test", chunk_size=30)
        assert len(chunks) >= 2

    def test_sentence_splitting(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        chunks = recursive_chunk_text(text, "doc1", "Test", chunk_size=30)
        assert len(chunks) >= 2

    def test_chunk_metadata(self) -> None:
        text = "A" * 2000
        chunks = recursive_chunk_text(text, "doc-42", "My Document")
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk["document_id"] == "doc-42"
            assert chunk["document_title"] == "My Document"
            assert "chunk_index" in chunk
            assert "content" in chunk

    def test_chunk_index_sequential(self) -> None:
        text = "A" * 5000
        chunks = recursive_chunk_text(text, "doc1", "Test", chunk_size=1000)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_no_overlap_when_small(self) -> None:
        text = "Hello world."
        chunks = recursive_chunk_text(text, "doc1", "Test", chunk_size=100, chunk_overlap=0)
        assert len(chunks) == 1

    def test_preserves_content(self) -> None:
        text = "The quick brown fox jumps over the lazy dog. " * 50
        chunks = recursive_chunk_text(text, "doc1", "Test", chunk_size=500)
        combined = "".join(c["content"] for c in chunks)
        # All original words should be present
        for word in ["quick", "brown", "fox", "lazy", "dog"]:
            assert word in combined

    def test_custom_separators(self) -> None:
        text = "Part A | Part B | Part C"
        chunks = recursive_chunk_text(
            text, "doc1", "Test", chunk_size=15, separators=[" | "]
        )
        assert len(chunks) >= 2
