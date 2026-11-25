"""Text metrics for comparing a speech pathway with a text pathway.

Word error rate is the usual ASR number: edit distance of the token
sequence, divided by the number of reference tokens. Character error rate
is the same on characters. Both are deterministic and have no model behind them.
"""

from typing import List, Sequence


def _levenshtein(left: Sequence, right: Sequence) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, item in enumerate(left, 1):
        current = [i]
        for j, other in enumerate(right, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            substitute = previous[j - 1] + (item != other)
            current.append(min(insert, delete, substitute))
        previous = current
    return previous[-1]


def tokens(text: str) -> List[str]:
    """Lower-case words with surrounding punctuation removed. Polish letters stay."""
    words = []
    for raw in text.replace("\n", " ").lower().split():
        cleaned = raw.strip(".,!?;:\"'()[]{}«»…")
        if cleaned:
            words.append(cleaned)
    return words


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate. An empty reference scores 0 only when the hypothesis is empty too."""
    ref = tokens(reference)
    hyp = tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / float(len(ref))


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate over the stripped lower-case strings, spaces included."""
    ref = list(reference.strip().lower())
    hyp = list(hypothesis.strip().lower())
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / float(len(ref))
