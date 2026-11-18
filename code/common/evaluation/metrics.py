"""
Reference-based text metrics, standard library only.

Every metric takes one prediction and one reference (strings) and returns a
float in [0, 1]. ``aggregate`` averages them over a batch. These are the
metrics the evaluation adapters compute themselves before handing results
to a tracking tool (MLflow, TensorBoard, W&B, LangSmith).

    exact_match   1 if normalized texts are equal
    contains      1 if the normalized reference occurs in the prediction
    token_f1      SQuAD-style token overlap F1
    rouge_l       ROUGE-L F-measure (longest common subsequence of tokens)
    numeric_match 1 if every number in the reference appears in the prediction

Normalization: lowercase, decimal comma -> dot, punctuation stripped,
whitespace collapsed. It is language-agnostic (works for Polish).
"""

import re
import string
from collections import Counter
from typing import Callable, Dict, List, Sequence

_PUNCT = re.compile(f"[{re.escape(string.punctuation)}„”«»–—…]")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def normalize_text(text: str) -> str:
    """Lowercase, unify decimal comma, drop punctuation, collapse whitespace."""
    text = str(text or "").lower()
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    text = _PUNCT.sub(lambda m: m.group(0) if m.group(0) == "." else " ", text)
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> List[str]:
    """Normalized tokens."""
    return normalize_text(text).split()


def exact_match(prediction: str, reference: str) -> float:
    """1.0 if the normalized strings are identical."""
    return float(normalize_text(prediction) == normalize_text(reference))


def contains(prediction: str, reference: str) -> float:
    """1.0 if the normalized reference is a substring of the prediction."""
    ref = normalize_text(reference)
    return float(bool(ref) and ref in normalize_text(prediction))


def token_f1(prediction: str, reference: str) -> float:
    """Harmonic mean of token precision and recall (multiset overlap)."""
    pred, ref = tokens(prediction), tokens(reference)
    if not pred or not ref:
        return float(pred == ref)
    common = sum((Counter(pred) & Counter(ref)).values())
    if common == 0:
        return 0.0
    precision, recall = common / len(pred), common / len(ref)
    return 2 * precision * recall / (precision + recall)


def _lcs(a: Sequence[str], b: Sequence[str]) -> int:
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b, start=1):
            current.append(previous[j - 1] + 1 if x == y else max(previous[j], current[j - 1]))
        previous = current
    return previous[-1]


def rouge_l(prediction: str, reference: str) -> float:
    """ROUGE-L F1 over tokens."""
    pred, ref = tokens(prediction), tokens(reference)
    if not pred or not ref:
        return float(pred == ref)
    lcs = _lcs(pred, ref)
    if lcs == 0:
        return 0.0
    precision, recall = lcs / len(pred), lcs / len(ref)
    return 2 * precision * recall / (precision + recall)


def numeric_match(prediction: str, reference: str) -> float:
    """1.0 if all numbers of the reference occur in the prediction (0 numbers -> 0)."""
    ref_numbers = {float(n) for n in _NUMBER.findall(normalize_text(reference))}
    if not ref_numbers:
        return 0.0
    pred_numbers = {float(n) for n in _NUMBER.findall(normalize_text(prediction))}
    return float(ref_numbers <= pred_numbers)


METRICS: Dict[str, Callable[[str, str], float]] = {
    "exact_match": exact_match,
    "contains": contains,
    "token_f1": token_f1,
    "rouge_l": rouge_l,
    "numeric_match": numeric_match,
}


def compute(predictions: Sequence[str], references: Sequence[str],
            metrics: Sequence[str] = tuple(METRICS)) -> Dict[str, List[float]]:
    """Per-example scores for each requested metric."""
    if len(predictions) != len(references):
        raise ValueError(f"{len(predictions)} predictions but {len(references)} references")
    unknown = [m for m in metrics if m not in METRICS]
    if unknown:
        raise ValueError(f"unknown metrics {unknown}; available: {sorted(METRICS)}")
    return {name: [METRICS[name](p, r) for p, r in zip(predictions, references)]
            for name in metrics}


def aggregate(per_example: Dict[str, List[float]]) -> Dict[str, float]:
    """Mean of each metric (empty batch -> 0.0)."""
    return {name: (sum(values) / len(values) if values else 0.0)
            for name, values in per_example.items()}
