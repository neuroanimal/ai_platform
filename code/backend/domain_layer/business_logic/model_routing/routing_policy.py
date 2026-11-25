"""
Choosing a local model for a request: profiles built from facts, and an explainable rule.

The hardware decides the shape of the rule (CPU only, 31 GB RAM): a model that
is not in memory first has to be read from disk, which costs seconds per GB,
so switching models is expensive and the model already loaded is preferred
unless another one is clearly better. Quality comes from measurements, not
from labels: a ``ModelProfile`` combines the facts Ollama reports (size,
capabilities, context, loaded or not) with the scores of our benchmarks.

``route`` scores every usable model as

    score = quality(task, language) - seconds / seconds_per_point
            + preference bonuses

where ``seconds`` is the measured median answer time plus, for a model not in
memory, its loading time (``load_seconds_per_gb`` x size). The decision lists
the reasons and the ranked alternatives, so the choice can be checked and
argued with. Models without a measurement for the task are used only when no
measured model is usable, and the reason says so.

Tasks: ``chat`` (bilingual reasoning benchmark, per language), ``documents``
(agent-RAG benchmark, plain RAG variant), ``tools`` (tool-use benchmark, best
mode; else the agent-RAG agent variants).
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

TASKS = ("chat", "documents", "tools")
LANGUAGES = ("pl", "en")
#: Name fragments of models trained for Polish.
POLISH_FAMILIES = ("bielik", "pllum")
_POLISH_LETTERS = re.compile(r"[ąćęłńóśźż]", re.IGNORECASE)
_POLISH_WORDS = re.compile(r"\b(jest|się|nie|jak|czy|ile|dla|oraz|który|która|jakie|jaki|"
                           r"jaka|co|to|na|proszę|dlaczego|kiedy|gdzie|mam|jestem|policz|"
                           r"razy|wynosi|mój|moja|opisz|napisz|podaj)\b", re.IGNORECASE)


class RoutingError(Exception):
    """No model can serve the request."""


def detect_language(text: str) -> str:
    """"pl" when the text looks Polish (diacritics or common words), else "en"."""
    text = str(text or "")
    if _POLISH_LETTERS.search(text) or len(_POLISH_WORDS.findall(text)) >= 1:
        return "pl"
    return "en"


@dataclass
class ModelProfile:  # pylint: disable=too-many-instance-attributes
    """Facts about one installed model plus its measured scores (0..1) and speed."""

    name: str
    size_gb: float = 0.0
    capabilities: Sequence[str] = ()
    loaded: bool = False
    context_trained: Optional[int] = None
    #: {"chat:pl": 0.78, "chat:en": 0.9, "documents": 0.9, "tools": 0.5}
    quality: Dict[str, float] = field(default_factory=dict)
    #: {"chat:pl": 6.0, ...} median seconds per answer
    seconds: Dict[str, float] = field(default_factory=dict)
    #: Where each score came from (report file names).
    sources: Dict[str, str] = field(default_factory=dict)

    @property
    def chat_capable(self) -> bool:
        """Generates text (not an embedding-only model)."""
        return "completion" in self.capabilities or not self.capabilities

    @property
    def polish(self) -> bool:
        """A model trained for Polish."""
        return any(family in self.name.lower() for family in POLISH_FAMILIES)

    def key(self, task: str, language: str) -> str:
        """Key of the measurement for a task ("chat:pl", "documents", "tools")."""
        return f"chat:{language}" if task == "chat" else task


@dataclass
class RoutingPreferences:  # pylint: disable=too-many-instance-attributes
    """The user's policy on top of the numbers.

    ``seconds_per_point``: how many seconds of waiting one whole point of
    quality is worth (default 600: a model 10 % better may take 60 s longer).
    ``polish_bonus``: added to Polish models for Polish requests.
    ``max_unloaded_gb``: models larger than this are not loaded for a request
    (None = no limit). ``pinned``: task -> model name, always used if installed.
    """

    seconds_per_point: float = 600.0
    load_seconds_per_gb: float = 3.0
    polish_bonus: float = 0.05
    max_unloaded_gb: Optional[float] = None
    excluded: Sequence[str] = ()
    pinned: Dict[str, str] = field(default_factory=dict)
    allow_unmeasured: bool = True


@dataclass
class RouteDecision:
    """The chosen model, why, and the ranked alternatives."""

    model: str
    task: str
    language: str
    score: float
    reasons: List[str]
    ranking: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form."""
        return dict(self.__dict__)


def _candidate(profile: ModelProfile, task: str, language: str,
               preferences: RoutingPreferences) -> Optional[Dict[str, Any]]:
    """Score of one model, or None when it cannot serve the task."""
    if not profile.chat_capable or profile.name in preferences.excluded:
        return None
    if not profile.loaded and preferences.max_unloaded_gb is not None \
            and profile.size_gb > preferences.max_unloaded_gb:
        return None
    key = profile.key(task, language)
    quality = profile.quality.get(key)
    seconds = profile.seconds.get(key) or profile.seconds.get(f"chat:{language}") or 0.0
    load = 0.0 if profile.loaded else profile.size_gb * preferences.load_seconds_per_gb
    bonus = preferences.polish_bonus if language == "pl" and profile.polish else 0.0
    reasons = []
    if quality is None:
        reasons.append(f"no measurement for {key}")
    else:
        reasons.append(f"{key} quality {quality:.2f} ({profile.sources.get(key, '?')})")
    reasons.append(f"~{seconds:.0f} s per answer" + (f" + ~{load:.0f} s to load "
                                                    f"{profile.size_gb:.1f} GB" if load else
                                                    ", already in memory"))
    if bonus:
        reasons.append(f"Polish model +{bonus:.2f}")
    if "thinking" in profile.capabilities:
        reasons.append("reasoning model (thinks before answering)")
    score = (quality or 0.0) - (seconds + load) / preferences.seconds_per_point + bonus
    return {"model": profile.name, "score": round(score, 3), "measured": quality is not None,
            "quality": quality, "seconds": round(seconds + load, 1), "reasons": reasons}


def route(profiles: Sequence[ModelProfile], task: str, language: str,
          preferences: Optional[RoutingPreferences] = None) -> RouteDecision:
    """Best model for ``task`` in ``language`` (see the module docstring)."""
    if task not in TASKS:
        raise RoutingError(f"task must be one of {TASKS}")
    language = language if language in LANGUAGES else "en"
    preferences = preferences or RoutingPreferences()
    by_name = {p.name: p for p in profiles}
    pinned = preferences.pinned.get(task)
    if pinned and pinned in by_name:
        return RouteDecision(pinned, task, language, 0.0, [f"pinned for {task}"], [])
    candidates = [c for c in (_candidate(p, task, language, preferences) for p in profiles)
                  if c is not None]
    measured = [c for c in candidates if c["measured"]]
    pool = measured or (candidates if preferences.allow_unmeasured else [])
    if not pool:
        raise RoutingError(f"no installed model can serve {task} in {language}")
    ranking = sorted(pool, key=lambda c: c["score"], reverse=True)
    best = ranking[0]
    reasons = list(best["reasons"])
    if not measured:
        reasons.insert(0, "no measured model is usable; chosen without benchmark data")
    if len(ranking) > 1:
        reasons.append(f"next best: {ranking[1]['model']} ({ranking[1]['score']:+.2f} "
                       f"vs {best['score']:+.2f})")
    return RouteDecision(best["model"], task, language, best["score"], reasons, ranking[:5])
