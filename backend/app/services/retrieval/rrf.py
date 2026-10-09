"""Reciprocal Rank Fusion (RRF) — merges BM25 and dense search results."""

from __future__ import annotations


def reciprocal_rank_fusion(
    bm25_results: list[dict],
    dense_results: list[dict],
    k: int = 60,
    top_k: int = 20,
) -> list[dict]:
    """Merge BM25 and dense results using Reciprocal Rank Fusion.

    Each result set's rankings are converted to scores via 1/(k + rank).
    Scores from both sets are summed per chunk, then the top_k results
    are returned sorted by combined score.
    """
    scores: dict[str, dict] = {}

    for rank, result in enumerate(bm25_results):
        chunk_id = result.get("chunk_id", result.get("content", ""))
        if chunk_id not in scores:
            scores[chunk_id] = {**result, "rrf_score": 0.0}
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    for rank, result in enumerate(dense_results):
        chunk_id = result.get("chunk_id", result.get("content", ""))
        if chunk_id not in scores:
            scores[chunk_id] = {**result, "rrf_score": 0.0}
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    # Sort by RRF score
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    return sorted_results[:top_k]
