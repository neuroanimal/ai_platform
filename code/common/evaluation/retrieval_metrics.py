"""
Retrieval quality metrics (standard library only).

For one query: ``ranked`` is the list of retrieved document ids, best first;
``relevant`` the set of ids that answer the query.

    hit_at_k          1 if any relevant id is among the first k
    reciprocal_rank   1 / rank of the first relevant id (0 if none retrieved)
    recall_at_k       share of relevant ids among the first k

``aggregate_retrieval`` averages them over queries (MRR = mean reciprocal rank).
"""

from typing import Dict, Iterable, List, Sequence


def hit_at_k(ranked: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """1.0 if a relevant id is in the top k."""
    wanted = set(relevant)
    return float(any(doc in wanted for doc in list(ranked)[:k]))


def reciprocal_rank(ranked: Sequence[str], relevant: Iterable[str]) -> float:
    """1/rank of the first relevant id, 0.0 when none is retrieved."""
    wanted = set(relevant)
    for position, doc in enumerate(ranked, start=1):
        if doc in wanted:
            return 1.0 / position
    return 0.0


def recall_at_k(ranked: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Share of relevant ids found in the top k (0.0 for an empty relevant set)."""
    wanted = set(relevant)
    if not wanted:
        return 0.0
    return len(wanted & set(list(ranked)[:k])) / len(wanted)


def score_query(ranked: Sequence[str], relevant: Iterable[str],
                ks: Sequence[int] = (1, 3, 5)) -> Dict[str, float]:
    """All metrics for one query."""
    relevant = list(relevant)
    scores = {f"hit@{k}": hit_at_k(ranked, relevant, k) for k in ks}
    scores.update({f"recall@{k}": recall_at_k(ranked, relevant, k) for k in ks})
    scores["rr"] = reciprocal_rank(ranked, relevant)
    return scores


def aggregate_retrieval(per_query: List[Dict[str, float]]) -> Dict[str, float]:
    """Mean of each metric; ``rr`` is reported as ``mrr``."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    means = {key: sum(q[key] for q in per_query) / len(per_query) for key in keys}
    means["mrr"] = means.pop("rr")
    return means
