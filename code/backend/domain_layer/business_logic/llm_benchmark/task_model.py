"""
Domain model of an LLM quality benchmark.

A *task* is one question asked in one or more languages, with the expected
answer and the name of the screening checker that can pre-assess the
model's reply (see ``ai_platform.common.evaluation.answer_screening``).
A *task set* is a named, versioned list of tasks - versioned because
changing a prompt changes what the numbers mean, so reports record the
task set name and version they were produced with.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence


class TaskSetError(ValueError):
    """Invalid task or task set definition."""


@dataclass(frozen=True)
class LocalizedPrompt:
    """Prompt and expected answer in one language."""

    prompt: str
    expected: str
    #: Known wrong answers the screening may mark 'incorrect' (phrase checker).
    rejected: Sequence[str] = ()


@dataclass(frozen=True)
class BenchmarkTask:
    """One question in several languages."""

    task_id: str
    category: str
    checker: Optional[str]
    languages: Dict[str, LocalizedPrompt] = field(default_factory=dict)

    def prompt(self, language: str) -> LocalizedPrompt:
        """The prompt in ``language``."""
        if language not in self.languages:
            raise TaskSetError(f"task {self.task_id!r} has no {language!r} prompt")
        return self.languages[language]


@dataclass(frozen=True)
class TaskSet:
    """Named, versioned collection of tasks."""

    name: str
    version: str
    tasks: Sequence[BenchmarkTask]
    description: str = ""

    def __post_init__(self) -> None:
        ids = [t.task_id for t in self.tasks]
        if len(ids) != len(set(ids)):
            raise TaskSetError(f"duplicate task ids in {self.name}: {ids}")
        if not self.tasks:
            raise TaskSetError(f"task set {self.name} is empty")

    @property
    def languages(self) -> List[str]:
        """Languages every task provides, in first-task order."""
        first = list(self.tasks[0].languages)
        return [lang for lang in first if all(lang in t.languages for t in self.tasks)]

    def select(self, languages: Optional[Sequence[str]] = None) -> List[str]:
        """Validate a language selection (default: all common languages)."""
        chosen = list(languages or self.languages)
        missing = [lang for lang in chosen if lang not in self.languages]
        if missing:
            raise TaskSetError(f"{self.name} has no prompts in {missing}; has {self.languages}")
        return chosen


def task_from_dict(data: Dict) -> BenchmarkTask:
    """Build a task from the plain-dict form used in task set modules and JSON."""
    try:
        return BenchmarkTask(
            task_id=data["id"], category=data.get("category", ""), checker=data.get("checker"),
            languages={lang: LocalizedPrompt(v["prompt"], v.get("expected", ""),
                                             tuple(v.get("rejected", ())))
                       for lang, v in data["languages"].items()})
    except (KeyError, TypeError) as exc:
        raise TaskSetError(f"invalid task definition {data!r}: {exc}") from exc
