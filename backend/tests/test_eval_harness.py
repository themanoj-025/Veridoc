"""Tests for the A1 eval harness slug→UUID document resolution.

`scripts/run_eval.py` previously passed gold-set slugs (e.g. `gutenberg_132`,
`arxiv_*`) verbatim to the retriever, which filters Chroma metadata by real
DB document UUIDs — every filtered question would have silently retrieved
nothing, corrupting the metrics. These tests lock in the resolver that now
lives in `app/services/evaluation.py` and the naive-path wiring.

IMPORTANT: everything is imported lazily inside fixtures/tests. Importing
``app.services.evaluation`` at module level would pull in
sentence-transformers → sklearn at pytest *collection* time, which
C-stack-overflows on this Python 3.14 environment.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "run_eval.py"


@pytest.fixture
def eval_mod():
    """Lazily import app.services.evaluation (heavy import chain)."""
    from app.services import evaluation as mod
    return mod


@pytest.fixture
def run_eval_mod():
    """Load scripts/run_eval.py lazily (heavy import chain)."""
    spec = importlib.util.spec_from_file_location("run_eval_under_test", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Slug normalization / matching ─────────────────────────

class TestSlugMatching:
    def test_normalize_strips_non_alphanumerics(self, eval_mod):
        assert eval_mod._normalize_slug("github_readme_express") == "githubreadmeexpress"
        assert eval_mod._normalize_slug("arXiv_2401.12345") == "arxiv240112345"

    def test_exact_slug_matches_filename(self, eval_mod):
        assert eval_mod._slug_matches("gutenberg132", "gutenberg_132.txt") is True

    def test_slug_with_suffix_matches_bare_filename(self, eval_mod):
        # gold slug 'synthetic_contract_001' → file 'synthetic_contract.txt'
        assert eval_mod._slug_matches("syntheticcontract001", "synthetic_contract.txt") is True

    def test_readme_slug_matches_md(self, eval_mod):
        assert eval_mod._slug_matches("githubreadmeexpress", "github_readme.md") is True

    def test_unrelated_slug_does_not_match(self, eval_mod):
        assert eval_mod._slug_matches("zzznope", "synthetic_contract.txt") is False

    def test_none_candidate_false(self, eval_mod):
        assert eval_mod._slug_matches("abc", None) is False


# ── Wildcards ────────────────────────────────────────────

class TestWildcards:
    @pytest.mark.asyncio
    async def test_star_returns_none(self, eval_mod):
        assert await eval_mod.resolve_document_ids("*") is None

    @pytest.mark.asyncio
    async def test_empty_returns_none(self, eval_mod):
        assert await eval_mod.resolve_document_ids("") is None

    @pytest.mark.asyncio
    async def test_prefix_star_returns_none(self, eval_mod):
        assert await eval_mod.resolve_document_ids("arxiv_*") is None


# ── Resolution against the DB ────────────────────────────

class TestResolution:
    """Resolution against a fake async DB session (patches the module-level
    async_session_factory used by resolve_document_ids)."""

    @pytest.fixture(autouse=True)
    def _reset_cache(self, eval_mod):
        eval_mod._SLUG_CACHE.clear()
        yield
        eval_mod._SLUG_CACHE.clear()

    def _fake_factory(self, rows):
        """Build a fake async_session_factory returning *rows*.

        The session is an AsyncMock (``await session.execute(...)``) but the
        *result* is a plain MagicMock: the resolver calls ``result.all()``
        synchronously, so an AsyncMock there would return an un-awaited
        coroutine ("coroutine object is not iterable").
        """
        fake_session = AsyncMock()
        fake_result = MagicMock()
        fake_result.all.return_value = rows
        fake_session.execute.return_value = fake_result
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=False)

        class FakeFactory:
            def __call__(self):
                return fake_session

        return FakeFactory()

    @pytest.mark.asyncio
    async def test_resolves_slug_to_uuid(self, eval_mod, monkeypatch):
        rows = [
            ("11111111-1111-1111-1111-111111111111", "gutenberg_132.txt", "The Art of War"),
            ("22222222-2222-2222-2222-222222222222", "synthetic_contract.txt", "License"),
        ]
        monkeypatch.setattr(eval_mod, "async_session_factory", self._fake_factory(rows))

        ids = await eval_mod.resolve_document_ids("gutenberg_132")
        assert ids == ["11111111-1111-1111-1111-111111111111"]

        # Second call is cached (no second DB round trip)
        ids2 = await eval_mod.resolve_document_ids("gutenberg_132")
        assert ids2 == ids

    @pytest.mark.asyncio
    async def test_contract_slug_suffix_matches(self, eval_mod, monkeypatch):
        rows = [
            ("33333333-3333-3333-3333-333333333333", "synthetic_contract.txt", "License"),
        ]
        monkeypatch.setattr(eval_mod, "async_session_factory", self._fake_factory(rows))

        ids = await eval_mod.resolve_document_ids("synthetic_contract_001")
        assert ids == ["33333333-3333-3333-3333-333333333333"]

    @pytest.mark.asyncio
    async def test_unmatched_slug_falls_back_to_none(self, eval_mod, monkeypatch):
        rows = [("11111111-1111-1111-1111-111111111111", "gutenberg_132.txt", "Art of War")]
        monkeypatch.setattr(eval_mod, "async_session_factory", self._fake_factory(rows))

        assert await eval_mod.resolve_document_ids("nope_does_not_exist") is None

    @pytest.mark.asyncio
    async def test_db_error_falls_back_to_none(self, eval_mod, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("db down")

        bad_session = AsyncMock()
        bad_session.__aenter__ = AsyncMock(side_effect=boom)
        bad_session.__aexit__ = AsyncMock(return_value=False)

        class BadFactory:
            def __call__(self):
                return bad_session

        monkeypatch.setattr(eval_mod, "async_session_factory", BadFactory())

        assert await eval_mod.resolve_document_ids("gutenberg_132") is None

    @pytest.mark.asyncio
    async def test_run_evaluation_uses_resolver(self, run_eval_mod, monkeypatch):
        """run_evaluation() in run_eval.py must call resolve_document_ids
        (not pass slugs raw) — wildcard questions must search all docs."""
        gold_qa = [
            {
                "id": "g-1",
                "document_id": "gutenberg_132",
                "question": "Who wrote The Art of War?",
                "gold_answer": "Sun Tzu",
                "type": "factual",
            },
            {
                "id": "u-1",
                "document_id": "*",
                "question": "Unanswerable?",
                "gold_answer": "n/a",
                "type": "unanswerable",
            },
        ]

        calls: list = []

        async def fake_run_single_eval(question, gold_answer, document_ids, use_hybrid):
            calls.append({"question": question, "document_ids": document_ids, "hybrid": use_hybrid})
            return {
                "question": question,
                "generated_answer": "Sun Tzu",
                "gold_answer": gold_answer,
                "faithfulness_score": 0.9,
                "latency_ms": 500,
            }

        async def fake_resolve(doc_id):
            return None if doc_id == "*" else ["uuid-1234"]

        monkeypatch.setattr(run_eval_mod, "run_single_eval", fake_run_single_eval)
        monkeypatch.setattr(run_eval_mod, "resolve_document_ids", fake_resolve)

        results, metrics = await run_eval_mod.run_evaluation(gold_qa, use_hybrid=True)

        assert len(results) == 2
        # Factual question must be filtered to the resolved UUID
        assert calls[0]["document_ids"] == ["uuid-1234"]
        # Wildcard question must search all docs
        assert calls[1]["document_ids"] is None
        assert metrics["total_questions"] == 2
        assert metrics["answer_accuracy"] == 1.0
        assert metrics["refusal_accuracy"] == 0.0


# ── use_hybrid wiring ────────────────────────────────────

class TestUseHybrid:
    """The `--compare` naive path must actually skip hybrid retrieval."""

    @pytest.mark.asyncio
    async def test_naive_path_does_not_use_hybrid(self, eval_mod, monkeypatch):
        """use_hybrid=False must take the dense-only branch (no HybridRetriever)."""
        import app.services.retrieval.dense as dense_mod

        calls = []

        async def fake_dense_search(query, document_ids=None, top_k=20):
            calls.append({"query": query, "document_ids": document_ids, "top_k": top_k})
            return [
                {"content": "chunk-a", "document_id": "uuid-1234", "score": 0.9},
                {"content": "chunk-b", "document_id": "uuid-1234", "score": 0.8},
                {"content": "chunk-c", "document_id": "uuid-1234", "score": 0.7},
                {"content": "chunk-d", "document_id": "uuid-1234", "score": 0.6},
                {"content": "chunk-e", "document_id": "uuid-1234", "score": 0.5},
                {"content": "chunk-f", "document_id": "uuid-1234", "score": 0.4},
            ]

        # The in-function import (`from app.services.retrieval.dense import
        # dense_search`) resolves through the dense module at call time, so
        # patch it there.
        monkeypatch.setattr(dense_mod, "dense_search", fake_dense_search)

        class FakeHybrid:
            def __init__(self):
                raise AssertionError("HybridRetriever must NOT be used on the naive path")

        # Regression guard: if someone re-wires the naive branch to construct
        # HybridRetriever, this raises and the test fails.
        monkeypatch.setattr(eval_mod, "HybridRetriever", FakeHybrid)

        class FakeLLM:
            model_name = "fake-model"

            async def chat(self, system_prompt, history, message):
                return "Sun Tzu wrote the Art of War."

        monkeypatch.setattr(eval_mod, "get_llm", lambda: FakeLLM())

        result = await eval_mod.run_single_eval(
            question="Who wrote the Art of War?",
            gold_answer="Sun Tzu",
            document_ids=None,
            use_hybrid=False,
        )
        assert calls, "dense_search should have been called"
        assert result["n_chunks_used"] == 5
        # FakeLLM returns non-numeric text → faithfulness defaults to 0.5
        assert result["faithfulness_score"] == 0.5
