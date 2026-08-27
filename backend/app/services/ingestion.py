"""Document ingestion pipeline — parse, OCR, chunk, embed, index."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_factory
from app.models.chunk import Chunk
from app.repositories import ChunkRepository, DocumentRepository
from app.services.chunking import recursive_chunk_text
from app.services.vector_store import get_vector_store

logger = structlog.get_logger(__name__)


def get_embedding_model() -> object:
    """Get the sentence-transformers embedding model.

    Checks the DI container first (see :class:`app.core.di.DIContainer`).
    Falls back to an uncached instance when no container is active.

    Returns an object with ``.encode(texts, show_progress_bar)`` that
    returns an object with ``.tolist()`` (e.g. a numpy array).
    """
    from app.core.di import get_di_container

    container = get_di_container()
    if container is not None:
        return container.get_or_create_embedding_model()
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model (standalone): all-MiniLM-L6-v2")
    model: object = SentenceTransformer("all-MiniLM-L6-v2")
    return model


async def process_document(
    document_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Process a document: parse → OCR-if-needed → chunk → embed → index."""
    session_maker = session_factory or async_session_factory

    async with session_maker() as session:
        doc_repo = DocumentRepository(session)
        chunk_repo = ChunkRepository(session)

        doc = await doc_repo.find_by_id(document_id)
        if not doc:
            logger.error(f"Document {document_id} not found")
            return

        try:
            # 1. Parse
            doc.status = "parsing"
            await session.flush()

            text, pages, ocr_used = parse_document(doc.file_path, doc.file_type)
            doc.ocr_used = ocr_used

            # 2. Chunk
            doc.status = "chunking"
            await session.flush()

            chunks = chunk_text(
                text, doc_id=str(doc.id), doc_title=doc.title, pages=pages
            )
            doc.chunk_count = len(chunks)

            # Save chunks to DB via repository
            chunk_models = [
                Chunk(
                    document_id=doc.id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    page_number=c.get("page_number"),
                    ocr_used=ocr_used,
                )
                for c in chunks
            ]
            db_chunks = await chunk_repo.create_batch(chunk_models)

            # 3. Embed
            doc.status = "embedding"
            await session.flush()

            model = get_embedding_model()
            texts_to_embed = [c["content"] for c in chunks]
            embeddings = model.encode(texts_to_embed, show_progress_bar=False).tolist()

            # 4. Index in Chroma
            doc.status = "indexing"
            await session.flush()

            vs = get_vector_store()
            chroma_ids = await vs.add_chunks(chunks, embeddings)

            # Update chunks with chroma IDs
            for chunk, chroma_id in zip(db_chunks, chroma_ids, strict=False):
                chunk.chroma_id = chroma_id

            # 5. Done
            doc.status = "indexed"
            doc.page_count = (
                max(pages.values())
                if pages
                else len(set(pages.values())) if pages else None
            )
            await session.commit()

            # Invalidate BM25 cache so subsequent queries pick up the new content
            # (lazy import avoids circular dep: ingestion → retrieval.bm25 → retrieval.dense → ingestion)
            from app.services.retrieval.bm25 import (
                invalidate_bm25_index as _invalidate,  # type: ignore[import]
            )

            _invalidate()
            logger.info(f"Document {doc.id} indexed with {len(chunks)} chunks")

        except (OSError, ValueError) as e:
            doc.status = "failed"
            doc.error_message = str(e)
            await session.commit()
            logger.exception(f"Failed to process document {doc.id}: {e}")


def parse_document(file_path: str, file_type: str) -> tuple[str, dict[int, int], bool]:
    """Parse a document file into plain text.

    Returns
    -------
    tuple[str, dict[int, int], bool]
        (full_text, page_map, ocr_used) where ocr_used indicates whether
        OCR was required to extract text from this document.
    """
    path = Path(file_path)
    ext = file_type.lower()

    if ext == "pdf":
        return _parse_pdf(path)
    elif ext == "docx":
        text, pages = _parse_docx(path)
        return text, pages, False
    elif ext == "txt":
        text, pages = _parse_txt(path)
        return text, pages, False
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _parse_pdf(path: Path) -> tuple[str, dict[int, int], bool]:
    """Parse a PDF file. Falls back to OCR if needed.

    Returns (text, page_map, ocr_used).
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text_parts = []
        page_map = {}  # char_offset -> page_number

        offset = 0
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
            page_map[offset] = i + 1
            offset += len(page_text)

        full_text = "\n".join(text_parts)

        # If extracted text is too sparse, try OCR
        if len(full_text.strip()) < 50:
            logger.info("PDF text extraction yielded little text, attempting OCR...")
            text, pages = _parse_pdf_ocr(path)
            return text, pages, True

        return full_text, page_map, False
    except (OSError, ValueError) as e:
        logger.warning(f"PDF parsing failed, falling back to OCR: {e}")
        text, pages = _parse_pdf_ocr(path)
        return text, pages, True


def _parse_pdf_ocr(path: Path) -> tuple[str, dict[int, int]]:
    """Parse a PDF using Tesseract OCR (for scanned documents)."""
    try:
        import pytesseract
        from pdf2image import convert_from_path

        images = convert_from_path(str(path), dpi=300)
        text_parts = []
        page_map = {}
        offset = 0

        for i, img in enumerate(images):
            page_text = pytesseract.image_to_string(img)
            text_parts.append(page_text)
            page_map[offset] = i + 1
            offset += len(page_text)

        return "\n".join(text_parts), page_map
    except ImportError:
        logger.error("pdf2image or pytesseract not installed, OCR unavailable")
        return "", {}


def _parse_docx(path: Path) -> tuple[str, dict[int, int]]:
    """Parse a DOCX file."""
    try:
        import docx

        doc = docx.Document(str(path))
        text_parts = []
        page_map = {}
        offset = 0

        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
                page_map[offset] = 1  # DOCX doesn't have reliable page numbers
                offset += len(para.text)

        return "\n".join(text_parts), page_map
    except (OSError, ValueError) as e:
        raise ValueError(f"Failed to parse DOCX: {e}")


def _parse_txt(path: Path) -> tuple[str, dict[int, int]]:
    """Parse a plain text file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text, {0: 1}


def chunk_text(
    text: str,
    doc_id: str,
    doc_title: str,
    pages: dict[int, int] | None = None,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> list[dict[str, Any]]:
    """Split text into chunks respecting natural language boundaries.

    Delegates to the recursive boundary-aware splitter in
    ``app.services.chunking`` which tries paragraph → sentence → word
    boundaries before falling back to character-level splits.
    """
    return recursive_chunk_text(
        text=text,
        doc_id=doc_id,
        doc_title=doc_title,
        pages=pages,
        chunk_size=chunk_size,
        chunk_overlap=overlap,
    )
