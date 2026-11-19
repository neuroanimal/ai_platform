"""
Rule-based screening of LLM benchmark answers (integrated from
``config/test_env/test_30a_analysis_v4_2.py``, version 4.2).

Screening is a *pre-assessment*, never a verdict: every result carries
``is_final_judgement: False``, anything a rule cannot decide goes to
``manual_review``, and reasoning, consistency and language quality are
always left to a human.

Checkers are registered by name. A benchmark record selects its checker
with the ``checker`` field; records from older reports without that field
are mapped from their ``test_id`` (``LEGACY_TEST_IDS``). Statuses:

    candidate_correct*            the rule found the expected result
    candidate_incorrect*          the rule found a wrong result
    candidate_partial_*           right conclusion, wrong detail
    manual_review                 undecidable, contradictory, unknown or truncated

Rules on truncated answers (``finish_reason == "length"``): a positive
verdict cannot stand (the answer may have continued differently) and goes
to manual review with ``pre_truncation_status``; a wrong claim already
written stays wrong.

Standard library only; messages are English (the test_env original was
Polish - the rules are the same).

Changes in 4.3 (from reading the manual-review cases of the first 9-model
Ollama run, 2026-11-19):

- an equation inside a chain is no longer read as a step:
  ``10 × 20 + ... + 7 × 3 = 200 + 30 + ...`` used to yield the false step
  "7 × 3 = 200";
- ``× 100%`` in a percentage formula is a factor, not a result:
  ``(12 / 100) * 100% = 12%`` used to count as two percentages (12 and 100).

Changes in 4.4: LaTeX markup is unwrapped before the rules run (39 of 264
answers in the 11-model run used it): ``\\times`` / ``\\cdot`` become
operators, ``12\\%`` a percentage, ``\\text{..}`` / ``\\boxed{..}`` their content,
and ``\\[ \\]`` / ``\\( \\)`` / ``\\,`` disappear. Before, "17 \\times 23 = 391"
was no multiplication and "= 12\\%" no percentage. A number followed by an
operator no longer counts as a declared result ("17 × 23 = 17 × (20 + 3)").

Changes in 4.5: generic checkers for new task sets - ``numeric`` (one expected
number), ``yes_no`` (decided by the first sentence) and ``phrase`` (one of
several accepted phrases; absence means manual review, never 'incorrect').

Changes in 4.6 (hand-check of the first v3 run): ``numeric`` reads thousands
separators ("2,500" / "2 500" = 2500, while "2,5" stays 2.5), number words
(PL/EN 0-20: "dwa razy" = 2) and counts ("3 razy", "3 times"); a wrong
declared value followed later by the expected one ("100 ÷ 7 = 14 with a
remainder of 2") goes to manual review instead of 'incorrect'.

Changes in 4.7: ``yes_no`` also reads an *explicit* final answer when the
first sentence does not decide - "the answer is yes", "odpowiedź: nie",
\\boxed{Yes}, or a sentence that starts with yes/no near the end. Restating
conclusions ("so 0.7 is greater") still go to manual review: inferring yes/no
from them would need language understanding the rules do not have.
"""

# One branch per outcome keeps each rule readable next to its message.
# pylint: disable=too-many-return-statements

import re
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

VERSION = "4.7"

Verdict = Tuple[str, str]
Checker = Callable[[Dict[str, Any]], Verdict]

# Multiplication operator: symbol or word (PL/EN).
MULT_OP = r"(?:[*x×·]|razy|times|multiplied\s+by|pomnożone\s+przez)"
# Verb/sign declaring a result.
RESULT_VERB = r"(?:=|equals|is|wynosi|daje|to|równa\s+się|gives)"
# A number, optionally wrapped in markdown emphasis (**391**).
NUMBER_AFTER = r"[\s*]*(\d+)(?![\d])"
# Generic "a op b = c" equation (intermediate steps).
# The left operand must start the expression and the result must end it, so a
# term of a longer chain ("... + 7 × 3 = 200 + 30") is not mistaken for a step.
EQUATION = re.compile(
    r"(?<![\d.])(?<![*x×·+\-]\s)(?<![*x×·+\-])(\d+)\s*([*x×·+\-])\s*(\d+)\s*=\s*(\d+)"
    r"(?![\d])(?!\s*[*x×·+\-]\s*[\d(])")
PERCENT = r"(\d+(?:\.\d+)?)\s*(?:%|procent\w*|percent)"
# "× 100%" in a formula is a conversion factor, not a stated result.
PERCENT_FACTOR = re.compile(r"[*x×·]\s*100\s*(?:%|procent\w*|percent)")

# Predicate forms that cannot be derived from the expected value
# (Polish case inflection).
PREDICATE_FORMS = {
    "ssakiem": [r"należy\s+do\s+ssaków", r"jest\s+przedstawicielem\s+ssaków"],
    "mammal": [r"belongs\s+to\s+the\s+mammals"],
}


_LATEX_REPLACEMENTS = (
    (re.compile(r"\\(?:text|textbf|mathrm|boxed|mathbf)\s*\{([^{}]*)\}"), r"\1"),
    (re.compile(r"\\times"), " × "),
    (re.compile(r"\\cdot"), " · "),
    (re.compile(r"\\%"), "%"),
    (re.compile(r"\\[,;:! ]"), " "),
    (re.compile(r"\\[\[\]()]"), " "),
)


def strip_latex(text: str) -> str:
    """Unwrap the LaTeX markup models use for formulas (see 4.4 above)."""
    for pattern, replacement in _LATEX_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def normalize(text: Any) -> str:
    """Unwrap LaTeX, lowercase, unify decimal comma, collapse whitespace."""
    text = strip_latex(str(text or "")).lower().replace(",", ".")
    return re.sub(r"\s+", " ", text).strip()


def fuzzy_word(word: str) -> str:
    """Regex for a word tolerant to doubled letters (Mruczek / Mrruczek)."""
    collapsed = re.sub(r"(.)\1+", r"\1", normalize(word))
    return r"\b" + "".join(re.escape(ch) + "+" for ch in collapsed if ch.strip()) + r"\b"


def technical_completeness(record: Dict[str, Any]) -> Dict[str, str]:
    """Was the answer cut off by the token limit?"""
    finish_reason = str(record.get("finish_reason", "")).lower()
    if finish_reason == "length":
        return {"status": "truncated", "evidence": "finish_reason=length"}
    if finish_reason == "stop":
        return {"status": "not_marked_truncated", "evidence": "finish_reason=stop"}
    return {"status": "unknown", "evidence": f"finish_reason={finish_reason or 'missing'}"}


# ============================================================================
# multiplication
# ============================================================================

def extract_operands(prompt: str) -> Optional[Tuple[int, int]]:
    """(a, b) of the multiplication asked in the prompt, or None."""
    match = re.search(rf"(\d+)\s*{MULT_OP}\s*(\d+)", normalize(prompt))
    return (int(match.group(1)), int(match.group(2))) if match else None


def find_result_claims(text: str, operands: Optional[Tuple[int, int]]) -> List[int]:
    """Numbers the answer declares as the result of a x b."""
    claims: List[int] = []
    if operands:
        a, b = operands
        for left, right in ((a, b), (b, a)):
            # The number must end the right-hand side: in "17 × 23 = 17 × (20 + 3)"
            # the 17 starts an expression and is no declared result.
            pattern = (rf"(?<![\d.]){left}\s*{MULT_OP}\s*{right}\s*\)?\s*"
                       rf"{RESULT_VERB}{NUMBER_AFTER}(?!\s*(?:{MULT_OP}|[+\-=(]))")
            claims.extend(int(v) for v in re.findall(pattern, text))
    # "result: 391" - but not "Result: 17 * 23 = 391", where 17 starts an operation.
    generic = (r"(?:wynik\w*|result|answer|odpowiedź)\s*(?:is|to|jest|wynosi|:|=)?"
               + NUMBER_AFTER + rf"(?!\s*(?:{MULT_OP}|[+\-=]))")
    claims.extend(int(v) for v in re.findall(generic, text))
    return claims


def check_equations(text: str, operands: Optional[Tuple[int, int]]):
    """(correct_steps, wrong_steps); the direct a x b = c restates, not calculates."""
    correct, wrong = [], []
    for left, operator, right, result in EQUATION.findall(text):
        x, y, z = int(left), int(right), int(result)
        if operator in "*x×·":
            value, direct = x * y, operands is not None and {x, y} == set(operands)
        elif operator == "+":
            value, direct = x + y, False
        else:
            value, direct = x - y, False
        step = f"{x} {operator} {y} = {z}"
        if value != z:
            wrong.append(step)
        elif not direct:
            correct.append(step)
    return correct, wrong


def check_multiplication(answer: str, expected: str, prompt: str = "") -> Verdict:
    """Screen an answer to 'what is a times b'."""
    text, expected = normalize(answer), normalize(expected)
    if not expected:
        return "manual_review", "No expected value."
    try:
        expected_value = int(expected)
    except ValueError:
        return "manual_review", "Unsupported expected-value format."
    operands = extract_operands(prompt)
    if operands and operands[0] * operands[1] != expected_value:
        return ("manual_review",
                f"Inconsistent expected value: {operands[0]} x {operands[1]} != {expected_value}.")

    claims = find_result_claims(text, operands)
    wrong_claims = sorted({c for c in claims if c != expected_value})
    claims_expected = expected_value in claims
    has_expected = bool(re.search(rf"(?<!\d){expected_value}(?!\d)", text))
    correct_steps, wrong_steps = check_equations(text, operands)

    if claims_expected and wrong_claims:
        return "manual_review", f"Contradictory results: {expected_value} and {wrong_claims}."
    if wrong_claims:
        return "candidate_incorrect", f"Declared result {wrong_claims}, expected {expected_value}."
    if claims_expected or has_expected:
        if wrong_steps:
            return ("manual_review",
                    f"Expected result present, but wrong intermediate steps: {wrong_steps[:3]}.")
        if correct_steps:
            return ("candidate_correct_with_calculation",
                    f"Expected result and correct calculation steps: {correct_steps[:3]}.")
        return ("candidate_correct_result_only",
                "Expected result present; the derivation was not confirmed.")
    return "manual_review", "The multiplication could not be assessed reliably."


# ============================================================================
# percentage
# ============================================================================

def check_percentage(answer: str, expected: str) -> Verdict:
    """Screen an answer whose expected value is a percentage."""
    match = re.search(PERCENT, normalize(expected))
    if not match:
        return "manual_review", "Unsupported expected-value format."
    expected_value = float(match.group(1))
    text = PERCENT_FACTOR.sub(" ", normalize(answer))
    found = sorted({float(v) for v in re.findall(PERCENT, text)})
    if not found:
        return "manual_review", "No percentage found."
    if len(found) > 1:
        return ("manual_review",
                f"Several percentages found: {found}. Possible contradiction or "
                "intermediate values.")
    if abs(found[0] - expected_value) < 1e-4:
        return "candidate_correct", f"Expected value {expected_value:g}% found."
    return "candidate_incorrect", f"Expected {expected_value:g}%, found {found}."


# ============================================================================
# syllogism
# ============================================================================

def parse_syllogism_expected(expected: str, language: str) -> Tuple[str, str]:
    """(subject, predicate) from e.g. 'Tak, Mruczek jest ssakiem.'"""
    text = normalize(expected)
    if language == "pl":
        match = re.search(r"(?:tak|nie)\W*\s*(\w+)\s+(?:nie\s+)?jest\s+(\w+)", text)
    else:
        match = re.search(r"(?:yes|no)\W*\s*(\w+)\s+is\s+(?:not\s+)?(?:an?\s+)?(\w+)", text)
    if match:
        return match.group(1), match.group(2)
    return ("mruczek", "ssakiem") if language == "pl" else ("mruczek", "mammal")


def check_syllogism(answer: str, language: str, expected: str = "") -> Verdict:
    """Screen the conclusion of a categorical syllogism."""
    if language not in ("pl", "en"):
        return "manual_review", f"Unsupported language: {language}."
    text = normalize(answer)
    subject, predicate = parse_syllogism_expected(expected, language)
    extra = "".join("|" + form for form in PREDICATE_FORMS.get(predicate, []))
    if language == "pl":
        predicate_pattern = rf"(?:jest\s+{re.escape(predicate)}{extra})"
        negation = r"\bnie\b|\bnigdy\b"
    else:
        predicate_pattern = (rf"(?:is\s+(?:not\s+)?(?:an?\s+)?{re.escape(predicate)}"
                             rf"|isn't\s+(?:an?\s+)?{re.escape(predicate)}{extra})")
        negation = r"\bnot\b|\bnever\b|\bisn't\b"
    pattern = re.compile(rf"{fuzzy_word(subject)}[^.!?]{{0,100}}?{predicate_pattern}", re.I)
    kinds = {"negative" if re.search(negation, m.group(0)) else "positive"
             for m in pattern.finditer(text)}
    if kinds == {"positive", "negative"}:
        return "manual_review", "Both an assertion and a negation of the property were found."
    if "positive" in kinds:
        return ("candidate_correct_conclusion",
                f"'{subject}' -> '{predicate}' asserted; the justification needs a separate check.")
    if "negative" in kinds:
        return "candidate_incorrect_conclusion", f"'{subject}' -> '{predicate}' negated."
    return "manual_review", "No clear assertion or negation of the property for the subject."


# ============================================================================
# currency vs CPI (topic-specific)
# ============================================================================

CURRENCY_PATTERNS = {
    "pl": {
        "correct_conclusion": [r"nie oznacza(?: to)? automatycznie", r"nie musi oznaczać",
                               r"nie powoduje automatycznie", r"nie wynika automatycznie",
                               r"nie prowadzi automatycznie do"],
        "incorrect_conclusion": [
            r"(?<!nie )automatycznie\s+(?:powoduje|oznacza|prowadzi do)\s+wzrost(?:u)?",
            r"(?<!nie )(?:oznacza|powoduje)\s+automatycznie\s+wzrost(?:u)?",
            r"zawsze powoduje wzrost",
            r"musi\s+prowadzić\s+do\s+wzrost(?:u)?"],
        "correct_direction": [
            r"(?:usd|dolar)[^.!?]{0,100}(?:drożej|więcej\s+złotych|kosztuje\s+więcej\s+pln)",
            r"(?:złoty|pln)[^.!?]{0,100}(?:słabnie|osłabia\s+się|traci\s+na\s+wartości)",
            r"(?:osłabienie|deprecjacja)\s+(?:złotego|pln)",
            r"za\s+(?:jednego\s+)?dolara[^.!?]{0,50}więcej\s+złotych"],
        "incorrect_direction": [
            r"(?:złoty|pln)[^.!?]{0,100}(?:umacnia\s+się|zyskuje\s+na\s+wartości)",
            r"(?:usd|dolar)[^.!?]{0,100}(?:tanieje|kosztuje\s+mniej\s+złotych)",
            r"(?:osłabienie|deprecjacja)\s+(?:dolara|usd)",
            r"(?:złoty|pln)[^.!?]{0,100}(?:jest\s+silniejszy|staje\s+się\s+silniejszy)"],
    },
    "en": {
        "correct_conclusion": [r"does not automatically mean", r"does not necessarily mean",
                               r"does not automatically cause", r"does not necessarily cause",
                               r"does not automatically lead to"],
        "incorrect_conclusion": [r"automatically means an increase",
                                 r"automatically causes an increase",
                                 r"always causes an increase", r"must lead to an increase",
                                 r"(?<!not )automatically leads? to an increase"],
        "correct_direction": [
            r"(?:usd|dollar)[^.!?]{0,100}(?:more expensive|costs more|higher in pln)",
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:weakens|depreciates|loses value)",
            r"(?:weakening|depreciation)\s+of\s+(?:the\s+)?(?:pln|zloty)",
            r"more\s+zloty[^.!?]{0,50}(?:per|for)\s+(?:one\s+)?dollar"],
        "incorrect_direction": [
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:strengthens|appreciates|gains value)",
            r"(?:usd|dollar)[^.!?]{0,100}(?:becomes cheaper|costs less)",
            r"(?:weakening|depreciation)\s+of\s+(?:the\s+)?(?:usd|dollar)",
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:becomes stronger|is stronger)"],
    },
}


def check_currency(answer: str, language: str) -> Verdict:
    """Screen 'does USD/PLN growth automatically mean CPI growth'."""
    patterns = CURRENCY_PATTERNS.get(language)
    if patterns is None:
        return "manual_review", f"Unsupported language: {language}."
    text = normalize(answer)
    found = {group: any(re.search(p, text) for p in items) for group, items in patterns.items()}
    if found["correct_conclusion"] and found["incorrect_conclusion"]:
        return "manual_review", "Contradictory statements on exchange rate vs CPI."
    if found["correct_direction"] and found["incorrect_direction"]:
        return "manual_review", "Contradictory readings of the USD/PLN direction."
    if found["incorrect_conclusion"]:
        return "candidate_incorrect_conclusion", "Suggests CPI rises automatically with the rate."
    if not found["correct_conclusion"]:
        return "manual_review", "No clear statement that the link is not automatic."
    if found["incorrect_direction"]:
        return ("candidate_partial_direction_error",
                "Correct conclusion, but the USD/PLN direction is misread.")
    if found["correct_direction"]:
        return ("candidate_correct_conclusion",
                "Correct conclusion and correct reading of a rising USD/PLN.")
    return ("candidate_correct_conclusion_direction_not_assessed",
            "Correct conclusion; the USD/PLN direction was not stated clearly.")


# ============================================================================
# generic checkers (screening 4.5): numeric answer, yes/no, expected phrase
# ============================================================================

NUMBER = r"-?\d+(?:\.\d+)?"
# Markers after which a number is a declared result, in PL and EN.
RESULT_MARKERS = (r"(?:=|equals|is|are|wynosi|wynoszą|to|jest|daje|gives|total|łącznie|razem|"
                  r"odpowiedź|answer|wynik\w*|result)")


def _as_number(text: str) -> Optional[float]:
    try:
        return float(text)
    except ValueError:
        return None


NUMBER_WORDS = {
    "zero": 0, "jeden": 1, "jedna": 1, "jedno": 1, "dwa": 2, "dwie": 2, "trzy": 3,
    "cztery": 4, "pięć": 5, "sześć": 6, "siedem": 7, "osiem": 8, "dziewięć": 9,
    "dziesięć": 10, "jedenaście": 11, "dwanaście": 12, "dwadzieścia": 20,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "twenty": 20,
}
_NUMBER_WORD = re.compile(r"\b(" + "|".join(NUMBER_WORDS) + r")\b")
# "2,500" / "2 500" (thousands) - but "2,5" (Polish decimal comma) stays.
_THOUSANDS = re.compile(r"(?<=\d)[, \u00a0](?=\d{3}(?!\d))")


def numeric_text(answer: str) -> str:
    """Normalized text with thousands separators removed and number words as digits."""
    text = _THOUSANDS.sub("", strip_latex(str(answer or "")))
    text = normalize(text)
    return _NUMBER_WORD.sub(lambda m: str(NUMBER_WORDS[m.group(1)]), text)


def check_numeric(answer: str, expected: str) -> Verdict:
    """Screen an answer whose expected value is one number (units ignored).

    Declared results are numbers after a result marker ("= 22", "wynosi 22",
    "answer: 22"), counts ("3 razy", "3 times") or emphasis (**22**,
    \\boxed{22}). Declarations are compared in order; when nothing is
    declared, the rule falls back to "the expected number occurs".
    """
    target = _as_number(normalize(expected).split()[0]) if normalize(expected) else None
    if target is None:
        return "manual_review", "Unsupported expected-value format."
    text = numeric_text(answer)
    patterns = (rf"{RESULT_MARKERS}\s*:?\s*\**\s*({NUMBER})(?![\d])(?!\s*[*x×·+\-/÷(])",
                rf"\*\*\s*({NUMBER})\s*\**",
                rf"(?<![\d.])({NUMBER})\s*(?:razy|times)\b(?!\s*\d)")
    declared = sorted((m.start(1), float(m.group(1)))
                      for pattern in patterns for m in re.finditer(pattern, text))
    values = [v for _, v in declared]
    right = [v for v in values if abs(v - target) < 1e-9]
    wrong = sorted({v for v in values if abs(v - target) >= 1e-9})
    occurrences = [m.start() for m in re.finditer(
        rf"(?<![\d.]){re.escape(f'{target:g}')}(?![\d])", text)]
    if right and wrong:
        if abs(values[-1] - target) < 1e-9:
            return ("candidate_correct_result_only",
                    f"Final declared result {target:g}; earlier values {wrong} (steps?).")
        return "manual_review", f"Declared {target:g} and {wrong}; final is {values[-1]:g}."
    if right:
        return "candidate_correct_result_only", f"Declared result {target:g}."
    if wrong:
        last_wrong = max(pos for pos, v in declared if abs(v - target) >= 1e-9)
        if any(pos > last_wrong for pos in occurrences):
            return ("manual_review",
                    f"Declared {wrong}, but {target:g} appears after it (e.g. a remainder).")
        return "candidate_incorrect", f"Declared {wrong}, expected {target:g}."
    if occurrences:
        return "candidate_correct_result_only", f"{target:g} occurs, no declared result."
    return "manual_review", "No declared result and the expected number does not occur."


YES = {"pl": r"\btak\b", "en": r"\byes\b"}
NO = {"pl": r"\bnie\b", "en": r"\bno\b"}


def check_yes_no(answer: str, expected: str, language: str) -> Verdict:
    """Screen a yes/no question by the answer's opening (first sentence)."""
    if language not in YES:
        return "manual_review", f"Unsupported language: {language}."
    want = "yes" if re.search(YES[language], normalize(expected)) else \
        "no" if re.search(NO[language], normalize(expected)) else None
    if want is None:
        return "manual_review", "Expected value is neither yes nor no."
    text = normalize(answer)
    opening = re.split(r"[.!?\n]", text, maxsplit=1)[0]
    says_yes = bool(re.search(YES[language], opening))
    says_no = bool(re.search(NO[language], opening))
    where = "Opens with"
    if says_yes == says_no:
        said = explicit_final_answer(text, language)
        if said is None:
            return "manual_review", "Neither the first sentence nor an explicit final answer " \
                                    "says yes or no unambiguously."
        where = "Final answer is"
    else:
        said = "yes" if says_yes else "no"
    if said == want:
        return "candidate_correct_conclusion", f"{where} '{said}'."
    return "candidate_incorrect_conclusion", f"{where} '{said}', expected '{want}'."


_FINAL_ANSWER = {
    "pl": r"(?:odpowiedź(?:\s+(?:brzmi|to|jest))?\s*:?|zatem|więc)\s*\**\s*(tak|nie)\b",
    "en": r"(?:answer\s+is|answer:|therefore|so)\s*:?\s*\**\s*(yes|no)\b",
}


def explicit_final_answer(text: str, language: str) -> Optional[str]:
    """'yes'/'no' stated explicitly near the end, else None (ambiguity is None too)."""
    sentences = [x.strip() for x in re.split(r"[.!?\n]", text) if x.strip()]
    tail = " . ".join(sentences[-3:])
    found = set(re.findall(_FINAL_ANSWER[language], tail))
    found |= set(re.findall(r"boxed\s*\{?\s*(yes|no|tak|nie)\b", text))
    # A later sentence that *starts* with yes/no counts, unless it also holds the
    # opposite word ("Tak i nie.") - the opening was already found ambiguous.
    opposite = {"yes": "no", "no": "yes", "tak": "nie", "nie": "tak"}
    for sentence in sentences[1:][-3:]:
        match = re.match(r"\**\s*(yes|no|tak|nie)\b", sentence)
        if match and not re.search(rf"\b{opposite[match.group(1)]}\b", sentence):
            found.add(match.group(1))
    kinds = {"yes" if w in ("yes", "tak") else "no" for w in found}
    return kinds.pop() if len(kinds) == 1 else None


def check_phrase(answer: str, expected: str) -> Verdict:
    """Screen a short factual answer: one of the '|'-separated phrases must occur.

    A missing phrase goes to manual review, not 'incorrect' - the answer may
    use a synonym, an inflected form or another spelling.
    """
    options = [normalize(o) for o in str(expected).split("|") if o.strip()]
    if not options:
        return "manual_review", "No expected phrase."
    text = normalize(answer)
    found = [o for o in options if re.search(rf"(?<!\w){re.escape(o)}(?!\w)", text)]
    if found:
        return "candidate_correct", f"Expected phrase found: {found[0]!r}."
    return "manual_review", f"None of {options} found; may be phrased differently."


# ============================================================================
# registry and record-level screening
# ============================================================================

CHECKERS: Dict[str, Checker] = {
    "multiplication": lambda r: check_multiplication(r.get("answer", ""), r.get("expected", ""),
                                                     r.get("prompt", "")),
    "percentage": lambda r: check_percentage(r.get("answer", ""), r.get("expected", "")),
    "syllogism": lambda r: check_syllogism(r.get("answer", ""), r.get("language", ""),
                                           r.get("expected", "")),
    "currency_vs_cpi": lambda r: check_currency(r.get("answer", ""), r.get("language", "")),
    "numeric": lambda r: check_numeric(r.get("answer", ""), r.get("expected", "")),
    "yes_no": lambda r: check_yes_no(r.get("answer", ""), r.get("expected", ""),
                                     r.get("language", "")),
    "phrase": lambda r: check_phrase(r.get("answer", ""), r.get("expected", "")),
}

#: test_id -> checker for reports written before records named their checker.
LEGACY_TEST_IDS = {
    "arithmetic_multiplication": "multiplication",
    "percentage_change": "percentage",
    "logical_syllogism": "syllogism",
    "currency_vs_inflation": "currency_vs_cpi",
}


def register_checker(name: str, checker: Checker) -> None:
    """Add a checker (explicit registration, no discovery)."""
    if name in CHECKERS:
        raise ValueError(f"checker {name!r} already registered")
    CHECKERS[name] = checker


def apply_truncation_rule(status: str, evidence: str, record: Dict[str, Any]):
    """(status, evidence, pre_truncation_status) after the truncation rule."""
    if technical_completeness(record)["status"] != "truncated":
        return status, evidence, None
    if not status.startswith("candidate_correct"):
        return status, evidence + " Answer truncated (finish_reason=length).", None
    return ("manual_review",
            f"Answer truncated (finish_reason=length) - preliminary '{status}' needs "
            f"confirmation. {evidence}", status)


def assess_answer(record: Dict[str, Any]) -> Dict[str, Any]:
    """Run the record's checker and the truncation rule."""
    name = record.get("checker") or LEGACY_TEST_IDS.get(record.get("test_id", ""))
    checker = CHECKERS.get(name) if name else None
    if record.get("status") == "FAIL":
        status, evidence = "manual_review", f"No answer (technical error): {record.get('error')}"
    elif checker is None:
        status, evidence = "manual_review", f"No checker for {name or record.get('test_id')!r}."
    else:
        status, evidence = checker(record)
    status, evidence, pre = apply_truncation_rule(status, evidence, record)
    return {"status": status, "evidence": evidence, "pre_truncation_status": pre,
            "checker": name, "is_final_judgement": False}


def detect_repetition(answer: str) -> Dict[str, Any]:
    """Sentences repeated verbatim (absence does not prove consistency)."""
    sentences = [normalize(s) for s in re.split(r"[.!?]\s+", str(answer or ""))]
    counts = Counter(s for s in sentences if len(s) > 20)
    repeated = [s for s, n in counts.items() if n > 1]
    return {"status": "repetition_detected" if repeated else "no_repetition_detected",
            "repeated_sentences": repeated[:5]}


MANUAL = {"status": "manual_review"}


def screen_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Screened copy of one benchmark record."""
    keep = ("model", "test_id", "checker", "category", "language", "run_index", "expected",
            "answer", "elapsed_seconds", "usage", "finish_reason")
    return {**{k: record.get(k) for k in keep}, "automatic_assessment": {
        "answer_screening": assess_answer(record),
        "technical_completeness": technical_completeness(record),
        "repetition": detect_repetition(record.get("answer", "")),
        "reasoning": dict(MANUAL), "consistency": dict(MANUAL),
        "language_quality": dict(MANUAL),
    }}


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Status counts per dimension and per model/language."""
    dimensions = ("answer_screening", "technical_completeness", "reasoning", "consistency",
                  "language_quality")
    counters = {d: Counter() for d in dimensions}
    by_model_language: Dict[str, Counter] = defaultdict(Counter)
    needs_review = truncated = 0
    for record in records:
        assessment = record["automatic_assessment"]
        for dimension in dimensions:
            counters[dimension][assessment[dimension]["status"]] += 1
        needs_review += any(assessment[d]["status"] == "manual_review" for d in dimensions)
        truncated += assessment["technical_completeness"]["status"] == "truncated"
        key = f'{record["model"]} / {record["language"]}'
        by_model_language[key][assessment["answer_screening"]["status"]] += 1
    return {"records": len(records), **{d: dict(c) for d, c in counters.items()},
            "truncated_records": truncated,
            "records_requiring_human_review": needs_review,
            "by_model_language": {k: dict(v) for k, v in sorted(by_model_language.items())}}


def screen_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Screen every record of a benchmark report (the report is not modified)."""
    records = report.get("results")
    if not isinstance(records, list):
        raise ValueError("report has no 'results' list")
    screened = [screen_record(r) for r in records]
    return {"screening_version": VERSION,
            "method": "deterministic_rule_based_screening_with_manual_review",
            "policy": {"automatic_screening_is_final_judgement": False,
                       "unknown_checkers_require_manual_review": True,
                       "truncated_positive_verdicts_require_manual_review": True},
            "summary": summarize(screened), "results": screened}
