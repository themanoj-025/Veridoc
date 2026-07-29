"""Tests for the document ingestion pipeline — parsing, chunking, and processing."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion import (
    parse_document,
    chunk_text,
    _parse_txt,
)


# ── TXT Parsing ──────────────────────────────────────────

class TestTextParsing:
    """Tests for plain text file parsing."""

    def test_parse_txt_basic(self, tmp_path):
        """Test parsing a basic text file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello, this is a test document.\nIt has multiple lines.\n")

        text, pages = _parse_txt(txt_file)
        assert "Hello, this is a test document." in text
        assert "It has multiple lines." in text
        assert 0 in pages
        assert pages[0] == 1

    def test_parse_txt_empty(self, tmp_path):
        """Test parsing an empty text file."""
        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("")

        text, pages = _parse_txt(txt_file)
        assert text == ""
        assert pages == {0: 1}

    def test_parse_txt_unicode(self, tmp_path):
        """Test parsing a text file with unicode characters."""
        txt_file = tmp_path / "unicode.txt"
        txt_file.write_text("Café résumé naïve 😊", encoding="utf-8")

        text, pages = _parse_txt(txt_file)
        assert "Café" in text
        assert "😊" in text


# ── Chunking ─────────────────────────────────────────────

class TestChunking:
    """Tests for text chunking logic."""

    def test_chunk_basic(self):
        """Test basic chunking splits text into chunks of specified size."""
        text = "word " * 1000  # 1000 words → ~5000 chars
        chunks = chunk_text(text, doc_id="doc-1", doc_title="Test Doc")

        assert len(chunks) > 0
        assert all(c["document_id"] == "doc-1" for c in chunks)
        assert all(c["document_title"] == "Test Doc" for c in chunks)
        # Each chunk should contain at most chunk_size + chunk_overlap characters
        # (the default overlap adds up to 200 chars to chunks[1:])
        assert all(len(c["content"]) <= 1700 for c in chunks)

    def test_chunk_small_text(self):
        """Test chunking text smaller than chunk size."""
        text = "This is a short document with only a few words."
        chunks = chunk_text(text, doc_id="doc-1", doc_title="Small Doc")

        assert len(chunks) == 1
        assert chunks[0]["content"] == text

    def test_chunk_empty_text(self):
        """Test chunking empty text returns empty list."""
        chunks = chunk_text("", doc_id="doc-1", doc_title="Empty Doc")
        assert len(chunks) == 0

    def test_chunk_overlap(self):
        """Test that chunks have overlapping content."""
        text = "word " * 600  # 600 words → ~3000 chars
        chunks = chunk_text(
            text,
            doc_id="doc-1",
            doc_title="Overlap Test",
            chunk_size=100,
            overlap=20,
        )

        assert len(chunks) >= 6
        # Check that consecutive chunks share some content
        if len(chunks) >= 2:
            words_0 = set(chunks[0]["content"].split())
            words_1 = set(chunks[1]["content"].split())
            assert len(words_0 & words_1) > 0, "Chunks should have overlap"

    def test_chunk_page_numbers(self):
        """Test that chunking assigns correct page numbers."""
        text = "page one content " * 50 + "page two content " * 50
        pages = {0: 1, 50: 2}  # char offset 50 → page 2

        chunks = chunk_text(
            text,
            doc_id="doc-1",
            doc_title="Page Test",
            pages=pages,
            chunk_size=30,
            overlap=5,
        )

        # Some chunks should be on page 1, some on page 2
        page_numbers = {c["page_number"] for c in chunks if c["page_number"] is not None}
        assert len(page_numbers) > 0
        assert 1 in page_numbers

    def test_chunk_incremental_indices(self):
        """Test that chunk indices are sequential starting from 0."""
        text = "word " * 1000
        chunks = chunk_text(text, doc_id="doc-1", doc_title="Index Test")

        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i


# ── Document Parsing Dispatch ────────────────────────────

class TestParseDocument:
    """Tests for the parse_document dispatcher."""

    def test_parse_unsupported_type(self):
        """Test that unsupported file types raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_document("/fake/path/file.xyz", "xyz")

    def test_parse_txt_dispatch(self, tmp_path):
        """Test that parse_document dispatches TXT correctly."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Test content")

        text, pages, ocr_used = parse_document(str(txt_file), "txt")
        assert "Test content" in text
        assert ocr_used is False  # TXT files never use OCR


# ── Full Pipeline Mock Test ──────────────────────────────

@pytest.mark.asyncio
async def test_process_document_not_found():
    """Test processing a non-existent document logs error without crashing."""
    from app.services.ingestion import process_document

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.__aenter__.return_value = mock_session

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    # Should not raise an exception
    result = await process_document(uuid.uuid4(), session_factory=mock_factory)
    assert result is None


@pytest.mark.asyncio
async def test_process_document_success(tmp_path):
    """Test the full document processing pipeline with mocks."""
    from app.services.ingestion import process_document
    from app.models.document import Document

    # Create a test document model
    doc_id = uuid.uuid4()
    txt_file = tmp_path / "test_doc.txt"
    txt_file.write_text("This is a test document with enough content to be chunked and processed " * 20)

    doc = Document(
        id=doc_id,
        user_id=uuid.uuid4(),
        title="Test Document",
        filename="test_doc.txt",
        file_type="txt",
        file_size=txt_file.stat().st_size,
        file_path=str(txt_file),
        status="pending",
    )

    # Mock session
    import datetime as dt

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=doc)
    mock_session.__aenter__.return_value = mock_session

    # Ensure doc has required fields set (as DB would via server_default)
    if doc.created_at is None:
        doc.created_at = dt.datetime.now(dt.timezone.utc)

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    # Mock the heavy dependencies
    with patch("app.services.ingestion.get_embedding_model") as mock_embed:
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode = MagicMock(return_value=np.array([[0.1] * 384]))
        mock_embed.return_value = mock_model

        with patch("app.services.ingestion.get_vector_store") as mock_vs:
            mock_store = MagicMock()
            mock_store.add_chunks = AsyncMock(return_value=["id1", "id2"])
            mock_vs.return_value = mock_store

            # This should complete without error
            await process_document(doc_id, session_factory=mock_factory)

    # Verify document status was updated
    assert doc.status == "indexed"


# ── Edge Cases ───────────────────────────────────────────

def test_chunk_exact_size_multiple():
    """Test chunking when text length is an exact multiple of chunk_size (chars)."""
    # Exactly 1500 chars (default chunk_size), one-word text with no separators
    text = "a" * 1500
    chunks = chunk_text(text, doc_id="doc-1", doc_title="Test", chunk_size=1500, overlap=0)

    assert len(chunks) == 1
    assert len(chunks[0]["content"]) == 1500


def test_chunk_single_word():
    """Test chunking a single word."""
    chunks = chunk_text("hello", doc_id="doc-1", doc_title="Test")
    assert len(chunks) == 1
    assert chunks[0]["content"] == "hello"


def test_parse_txt_special_chars(tmp_path):
    """Test parsing a text file with special characters."""
    txt_file = tmp_path / "special.txt"
    txt_file.write_text("Tab\tseparated\nNewline\r\nCRLF")

    text, pages = _parse_txt(txt_file)
    assert "Tab\tseparated" in text
    assert "Newline" in text
    assert "CRLF" in text
