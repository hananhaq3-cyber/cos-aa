"""
Unit tests for hybrid memory retrieval and ranking.
"""
from datetime import datetime, timedelta, timezone

import pytest

from src.memory.retrieval_ranker import (
    compute_keyword_score,
    compute_recency_factor,
    rank_results,
)
from src.memory.vector_store.interface import VectorSearchResult


def _make_vector_result(
    content: str,
    score: float,
    importance: float = 0.5,
    created_at: str = "2026-03-09T00:00:00+00:00",
    tags: str = "",
) -> VectorSearchResult:
    """Helper to build a VectorSearchResult for testing."""
    return VectorSearchResult(
        doc_id="test",
        content=content,
        score=score,
        metadata={
            "importance_score": str(importance),
            "created_at": created_at,
            "tags": tags,
            "summary": content[:200],
        },
    )


class TestComputeRecencyFactor:
    def test_today_recency_near_one(self):
        """A document created now should have recency close to 1.0."""
        now = datetime.now(timezone.utc)
        assert compute_recency_factor(now) == pytest.approx(1.0, abs=0.01)

    def test_old_document_recency_decays(self):
        """A document from 30 days ago should have significantly lower recency."""
        old = datetime.now(timezone.utc) - timedelta(days=30)
        factor = compute_recency_factor(old)
        assert factor < 0.1  # e^(-30 * 0.1) ≈ 0.05

    def test_naive_datetime_treated_as_utc(self):
        """Naive datetimes should still work (treated as UTC)."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        factor = compute_recency_factor(now)
        assert factor == pytest.approx(1.0, abs=0.01)


class TestComputeKeywordScore:
    def test_all_keywords_match(self):
        score = compute_keyword_score("python programming language", ["python", "programming"])
        assert score == 1.0

    def test_partial_match(self):
        score = compute_keyword_score("python programming", ["python", "java"])
        assert score == 0.5

    def test_no_match(self):
        score = compute_keyword_score("unrelated content", ["python"])
        assert score == 0.0

    def test_empty_keywords_returns_zero(self):
        score = compute_keyword_score("any content", [])
        assert score == 0.0


class TestRankResults:
    def test_higher_cosine_similarity_wins(self):
        """When only cosine similarity differs, highest similarity should rank first."""
        results = [
            _make_vector_result("low relevance", score=0.3),
            _make_vector_result("high relevance", score=0.95),
        ]
        ranked = rank_results(results, [], "test query")
        assert ranked[0].content == "high relevance"

    def test_keyword_boost(self):
        """Items matching query keywords should get boosted."""
        results = [
            _make_vector_result("something about python programming", score=0.5),
            _make_vector_result("general information", score=0.5),
        ]
        ranked = rank_results(results, [], "python")
        assert ranked[0].content == "something about python programming"

    def test_recency_effect(self):
        """More recent items should score higher on recency component."""
        results = [
            _make_vector_result("old item", score=0.5, created_at="2024-01-01T00:00:00+00:00"),
            _make_vector_result("new item", score=0.5, created_at="2026-03-08T00:00:00+00:00"),
        ]
        ranked = rank_results(results, [], "test query")
        assert ranked[0].content == "new item"

    def test_importance_weight(self):
        """Higher importance score should rank higher."""
        results = [
            _make_vector_result("low importance", score=0.5, importance=0.1),
            _make_vector_result("high importance", score=0.5, importance=0.9),
        ]
        ranked = rank_results(results, [], "test query")
        assert ranked[0].content == "high importance"

    def test_empty_results(self):
        """Empty input returns empty output."""
        ranked = rank_results([], [], "test")
        assert ranked == []

    def test_combined_score_produces_positive(self):
        """The hybrid formula should produce a positive composite score."""
        results = [
            _make_vector_result("perfect match", score=1.0, importance=1.0, tags="match"),
        ]
        ranked = rank_results(results, [], "match")
        assert ranked[0].relevance_score > 0
