"""Recursive boundary-aware text chunking.

Replaces the naive fixed-word-count ``chunk_text()`` with a recursive
splitter that respects natural language boundaries:

  1. Try paragraph boundaries (``\\n\\n``)
  2. Try line boundaries (``\\n``)
  3. Try sentence boundaries (``. `` ``! `` ``? ``)
  4. Try clause boundaries (``; ``)
  5. Fall back to word boundaries (`` ``)
  6. Last resort: character-level split

This produces chunks that preserve paragraph and sentence structure,
which significantly improves retrieval quality compared to arbitrary
word-count splits.

Separators are preserved (attached to the preceding piece during
splitting) so that merging small pieces reconstructs the original text
faithfully — words stay separated by spaces, paragraphs by blank lines.
"""

from __future__ import annotations

import re
from typing import Any


# Ordered by priority: most semantic first, fallback last
_DEFAULT_SEPARATORS = [
    "\n\n",   # Paragraphs
    "\n",     # Lines
    ". ",     # Sentences (period + space)
    "! ",     # Sentences (exclamation + space)
    "? ",     # Sentences (question + space)
    "; ",     # Clauses
    " ",      # Words
    "",       # Characters (last resort)
]


def recursive_chunk_text(
    text: str,
    doc_id: str,
    doc_title: str,
    pages: dict[int, int] | None = None,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
    separators: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Split ``text`` into chunks respecting natural language boundaries.

    Parameters
    ----------
    text : str
        The full document text.
    doc_id : str
        Document identifier (passed through to each chunk).
    doc_title : str
        Document title (passed through to each chunk).
    pages : dict[int, int] | None
        Mapping of ``char_offset → page_number`` from the parser.
    chunk_size : int
        Target chunk size in **characters** (not words).  Default 1500.
    chunk_overlap : int
        Number of overlapping characters between consecutive chunks.
        Default 200.
    separators : list[str] | None
        Ordered list of separators to try.  ``None`` uses the default list.

    Returns
    -------
    list[dict]
        Each dict has keys: ``document_id``, ``document_title``,
        ``chunk_index``, ``content``, ``page_number``.
    """
    if not text or not text.strip():
        return []

    seps = separators or _DEFAULT_SEPARATORS

    # 1. Recursively split into pieces ≤ chunk_size
    pieces = _recursive_split(text, seps, chunk_size)

    # 2. Merge small consecutive pieces up to chunk_size
    merged = _merge_splits(pieces, chunk_size)

    # 3. Apply overlap so context isn't lost at boundaries
    if chunk_overlap > 0 and len(merged) > 1:
        merged = _add_overlap(merged, chunk_overlap)

    # 4. Build chunk records with metadata
    chunks: list[dict[str, Any]] = []
    char_offset = 0
    for idx, content in enumerate(merged):
        if not content:
            continue
        page_number = _find_page_number(char_offset, pages)
        chunks.append({
            "document_id": doc_id,
            "document_title": doc_title,
            "chunk_index": idx,
            "content": content,
            "page_number": page_number,
        })
        char_offset += len(content)

    return chunks


def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """Split ``text`` recursively using the ordered ``separators``.

    Separators are preserved (attached to the preceding piece) so that
    merging small pieces back together faithfully reproduces the original
    text with all its separators intact.
    """
    if len(text) <= chunk_size:
        return [text] if text else []

    separator = separators[0]
    remaining = separators[1:]

    if not separator:
        # Last resort — character-level split
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    # Split while preserving the separator on each piece
    pieces = _split_preserving_sep(text, separator)

    result: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if len(piece) <= chunk_size:
            result.append(piece)
        else:
            if remaining:
                result.extend(_recursive_split(piece, remaining, chunk_size))
            else:
                result.extend(_recursive_split(piece, [""], chunk_size))

    return result


def _split_preserving_sep(text: str, separator: str) -> list[str]:
    """Split ``text`` on ``separator``, attaching the separator to each piece.

    Example::

        _split_preserving_sep("word1 word2 word3", " ")
        # → ["word1 ", "word2 ", "word3"]

    This guarantees that joining the pieces back together with ``str.join("")``
    faithfully reconstructs the original text.
    """
    if not separator:
        return list(text)

    escaped = re.escape(separator)
    raw = re.split(f"({escaped})", text)
    # raw = ["part1", "sep", "part2", "sep", "part3"]

    result: list[str] = []
    i = 0
    while i < len(raw):
        if i + 1 < len(raw) and re.fullmatch(escaped, raw[i + 1]):
            result.append(raw[i] + raw[i + 1])
            i += 2
        else:
            result.append(raw[i])
            i += 1

    return result


def _merge_splits(splits: list[str], chunk_size: int) -> list[str]:
    """Join consecutive small pieces back together until they reach chunk_size."""
    merged: list[str] = []
    current = ""

    for split in splits:
        if not current:
            current = split
        elif len(current) + len(split) <= chunk_size:
            current += split
        else:
            merged.append(current)
            current = split

    if current:
        merged.append(current)

    return merged


def _add_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    """Prepend the tail of each previous chunk to the current chunk."""
    result = [chunks[0]]

    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        curr = chunks[i]
        tail = prev[-overlap_chars:] if len(prev) > overlap_chars else prev
        result.append(tail + curr)

    return result


def _find_page_number(char_offset: int, pages: dict[int, int] | None) -> int | None:
    """Map a character offset to its page number using the offset→page map."""
    if not pages:
        return None
    sorted_offsets = sorted(pages.keys())
    for off in reversed(sorted_offsets):
        if char_offset >= off:
            return pages[off]
    return None
