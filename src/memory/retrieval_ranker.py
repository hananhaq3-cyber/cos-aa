"""
Hybrid retrieval ranker combining vector similarity, importance, recency, and keyword matching.

score = (0.6 * cosine_similarity) + (0.2 * importance) + (0.1 * recency) + (0.1 * keyword_match)
"""
import math
from datetime import datetime, timezone

from src.core.domain_objects import MemoryFragment, MemorySourceType, MemoryTier
from src.memory.vector_store.interface import VectorSearchResult

WEIGHT_SIMILARITY = 0.6
WEIGHT_IMPORTANCE = 0.2
WEIGHT_RECENCY = 0.1
WEIGHT_KEYWORD = 0.1
RECENCY_DECAY_RATE = 0.1


def compute_recency_factor(created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days_old = max(0, (now - created_at).total_seconds() / 86400)
    return math.exp(-days_old * RECENCY_DECAY_RATE)


def compute_keyword_score(content: str, query_terms: list[str]) -> float:
    if not query_terms:
        return 0.0
    content_lower = content.lower()
    matches = sum(1 for term in query_terms if term.lower() in content_lower)
    return matches / len(query_terms)


def rank_results(
    vector_results: list[VectorSearchResult],
    episodic_results: list[dict],
    query: str,
    top_k: int = 5,
) -> list[MemoryFragment]:
    query_terms = query.split()
    scored: list[tuple[float, MemoryFragment]] = []

    for vr in vector_results:
        importance = float(vr.metadata.get("importance_score", 0.5))
        created_str = vr.metadata.get("created_at", "")
        try:
            created = (
                datetime.fromisoformat(created_str)
                if created_str
                else datetime.now(timezone.utc)
            )
        except ValueError:
            created = datetime.now(timezone.utc)

        recency = compute_recency_factor(created)
        keyword = compute_keyword_score(vr.content, query_terms)

        score = (
            WEIGHT_SIMILARITY * vr.score
            + WEIGHT_IMPORTANCE * importance
            + WEIGHT_RECENCY * recency
            + WEIGHT_KEYWORD * keyword
        )

        scored.append((
            score,
            MemoryFragment(
                tier=MemoryTier.SEMANTIC,
                content=vr.content,
                summary=vr.metadata.get("summary", vr.content[:200]),
                relevance_score=score,
                source_type=MemorySourceType(
                    vr.metadata.get("source_type", "EPISODIC")
                ),
                created_at=created,
                tags=(
                    vr.metadata.get("tags", "").split(",")
                    if vr.metadata.get("tags")
                    else []
                ),
            ),
        ))

    for ep in episodic_results:
        content_str = str(ep.get("content", ""))
        importance = ep.get("importance_score", 0.5)
        created_str = ep.get("created_at", "")
        try:
            created = (
                datetime.fromisoformat(created_str)
                if created_str
                else datetime.now(timezone.utc)
            )
        except ValueError:
            created = datetime.now(timezone.utc)

        recency = compute_recency_factor(created)
        keyword = compute_keyword_score(content_str, query_terms)
        similarity = 0.3

        score = (
            WEIGHT_SIMILARITY * similarity
            + WEIGHT_IMPORTANCE * importance
            + WEIGHT_RECENCY * recency
            + WEIGHT_KEYWORD * keyword
        )

        scored.append((
            score,
            MemoryFragment(
                tier=MemoryTier.EPISODIC,
                content=content_str,
                summary=content_str[:200],
                relevance_score=score,
                source_type=MemorySourceType.EPISODIC,
                created_at=created,
                tags=ep.get("tags", []),
            ),
        ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [fragment for _, fragment in scored[:top_k]]
