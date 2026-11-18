import json
import re
from collections import defaultdict
from pathlib import Path


INPUT = Path("results/test_30_bilingual_quality.json")
OUTPUT = Path("results/test_30a_analysis_v1.json")


def contains(pattern, text):
    return bool(re.search(pattern, text, re.IGNORECASE))


def evaluate_answer(item):
    task = item["test_id"]
    answer = item.get("answer", "")
    language = item.get("language", "").lower()

    if task == "arithmetic_multiplication":
        correct = contains(r"(?<!\d)391(?!\d)", answer)
        return {
            "status": "correct" if correct else "incorrect",
            "method": "expected_numeric_value",
            "evidence": "391" if correct else "Expected result 391 not found",
        }

    if task == "percentage_change":
        correct = contains(
            r"(?<!\d)12\s*(?:%|procent(?:y|ów)?|percent)",
            answer,
        )
        return {
            "status": "correct" if correct else "incorrect",
            "method": "expected_percentage",
            "evidence": "12%" if correct else "Expected percentage 12% not found",
        }

    if task == "logical_syllogism":
        if language == "pl":
            positive = contains(r"\bjest\s+ssakiem\b", answer)
            negative = contains(r"\bnie\s+jest\s+ssakiem\b", answer)
        else:
            positive = contains(r"\bis\s+a\s+mammal\b", answer)
            negative = contains(r"\bis\s+not\s+a\s+mammal\b|\bisn't\s+a\s+mammal\b", answer)

        if positive and not negative:
            status = "correct"
        elif negative and not positive:
            status = "incorrect"
        else:
            status = "ambiguous_manual_review"

        return {
            "status": status,
            "method": "conclusion_phrase",
            "evidence": {
                "positive_conclusion_detected": positive,
                "negative_conclusion_detected": negative,
            },
        }

    if task == "currency_vs_inflation":
        if language == "pl":
            no_automatic_relation = (
                contains(r"\bnie\b", answer)
                and contains(r"automatycz|bezpośredni|sam.*wzrost", answer)
            )
        else:
            no_automatic_relation = (
                contains(r"\bno\b", answer)
                and contains(r"automatic|automatically|directly", answer)
            )

        return {
            "status": (
                "correct_conclusion_candidate"
                if no_automatic_relation
                else "manual_review"
            ),
            "method": "conclusion_heuristic",
            "evidence": "Conclusion requires semantic verification",
        }

    return {
        "status": "not_assessed",
        "method": "none",
        "evidence": "Unknown task",
    }


def evaluate_reasoning(item):
    task = item["test_id"]
    answer = item.get("answer", "")
    language = item.get("language", "").lower()

    if task == "arithmetic_multiplication":
        equation = contains(
            r"17\s*[*x×]\s*23\s*=\s*391|17\s*razy\s*23\s*=\s*391",
            answer,
        )
        return {
            "status": "supported" if equation else "manual_review",
            "evidence": "Explicit multiplication equation detected"
            if equation else "No reliably recognized complete equation",
        }

    if task == "percentage_change":
        has_difference = contains(
            r"12\s*(?:PLN|zł|zl|zlotych|złotych)",
            answer,
        )
        has_percentage = contains(
            r"12\s*(?:%|procent|percent)",
            answer,
        )
        if has_difference and has_percentage:
            status = "partially_supported"
        else:
            status = "manual_review"

        return {
            "status": status,
            "evidence": {
                "difference_of_12_detected": has_difference,
                "percentage_of_12_detected": has_percentage,
            },
        }

    if task == "logical_syllogism":
        return {
            "status": "manual_review",
            "evidence": "Premise-to-conclusion validity requires semantic review",
        }

    if task == "currency_vs_inflation":
        if language == "pl":
            wrong_direction = contains(
                r"PLN.{0,50}(?:umacnia|silniejsz|więcej.*USD)|"
                r"więcej\s+USD.{0,40}PLN|"
                r"złot(?:y|ów).{0,40}więcej\s+wart",
                answer,
            )
            correct_direction = contains(
                r"słabsz.{0,30}PLN|osłab.{0,30}PLN|"
                r"więcej\s+złotych.{0,30}dol|"
                r"import.{0,60}(?:droższ|wyższ)",
                answer,
            )
        else:
            wrong_direction = contains(
                r"PLN.{0,50}(?:stronger|more valuable|appreciat)|"
                r"more valuable.{0,50}PLN|"
                r"more expensive for US buyers",
                answer,
            )
            correct_direction = contains(
                r"weaker PLN|PLN depreciat|"
                r"more zlotys.{0,50}dollar|"
                r"imports?.{0,60}more expensive",
                answer,
            )

        if wrong_direction:
            status = "potential_direction_error"
        elif correct_direction:
            status = "direction_supported"
        else:
            status = "manual_review"

        return {
            "status": status,
            "evidence": {
                "potential_wrong_direction": wrong_direction,
                "correct_direction_cue": correct_direction,
            },
        }

    return {
        "status": "not_assessed",
        "evidence": "Unknown task",
    }


def evaluate_consistency(item):
    answer = item.get("answer", "")
    sentences = [
        re.sub(r"\s+", " ", s.strip().lower())
        for s in re.split(r"[.!?]+", answer)
        if len(s.strip()) > 20
    ]

    duplicates = sorted({
        sentence for sentence in sentences
        if sentences.count(sentence) > 1
    })

    return {
        "status": "repetition_detected" if duplicates else "no_repetition_detected",
        "repeated_sentences": duplicates[:5],
        "note": "No repetition detected does not prove logical consistency",
    }


def evaluate_completeness(item, max_tokens):
    finish_reason = item.get("finish_reason")
    usage = item.get("usage", {})
    completion_tokens = usage.get("completion_tokens")

    if finish_reason == "length":
        status = "truncated"
    elif not item.get("answer", "").strip():
        status = "empty"
    else:
        status = "not_truncated"

    return {
        "status": status,
        "finish_reason": finish_reason,
        "completion_tokens": completion_tokens,
        "configured_max_tokens": max_tokens,
    }


def analyze():
    with INPUT.open(encoding="utf-8") as f:
        source = json.load(f)

    analyzed = []

    for item in source["results"]:
        result = {
            "model": item["model"],
            "test_id": item["test_id"],
            "category": item["category"],
            "language": item["language"],
            "source_status": item.get("status"),
            "elapsed_seconds": item.get("elapsed_seconds"),
            "usage": item.get("usage"),
            "answer_correctness": evaluate_answer(item),
            "reasoning_correctness": evaluate_reasoning(item),
            "consistency": evaluate_consistency(item),
            "completeness": evaluate_completeness(
                item, source.get("max_tokens")
            ),
            "language_quality": {
                "status": "manual_review",
                "note": "Not reliably measurable with deterministic text rules",
            },
        }
        analyzed.append(result)

    summary = defaultdict(lambda: defaultdict(int))

    for item in analyzed:
        key = f'{item["model"]} / {item["language"]}'
        summary[key][item["answer_correctness"]["status"]] += 1
        summary[key][
            f'completeness:{item["completeness"]["status"]}'
        ] += 1

    report = {
        "test": "30A",
        "name": "Deterministic analysis of Test 30 bilingual results",
        "source": str(INPUT),
        "analysis_method": "rule_based_heuristics_with_manual_review_flags",
        "dimensions": [
            "answer_correctness",
            "reasoning_correctness",
            "consistency",
            "completeness",
            "language_quality",
        ],
        "summary": {
            key: dict(value) for key, value in summary.items()
        },
        "results": analyzed,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=== TEST 30A: ANALYSIS ===")
    print(f"Source: {INPUT}")
    print(f"Output: {OUTPUT}")
    print(f"Analyzed records: {len(analyzed)}")

    for key, values in report["summary"].items():
        print(f"\n{key}")
        for status, count in values.items():
            print(f"  {status}: {count}")

    print("\nAnalysis completed.")


if __name__ == "__main__":
    analyze()
