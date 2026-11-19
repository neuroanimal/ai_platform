"""
Question-answering test sets for RAG (retrieval + generation).

A QA set is a corpus and questions with the expected answer, the checker
that screens the answer (``common.evaluation.answer_screening``) and the
document that holds the answer. Half of the questions are about invented
facts (a fictional company, project and product) that no model can know:
answered correctly only when retrieval brings the right document, they show
what RAG adds over the closed-book model. The other half are general
knowledge, which shows whether context helps or distracts. The invented
facts avoid guessable values (a first draft used "until 18:00" and "12 electric
trucks", which closed-book models hit by chance).

``bilingual_qa`` v1: the 12 documents of ``bilingual_retrieval`` plus 6
documents about the fictional firm "Nordwind Logistyka"; 12 questions, half
in Polish, half in English, most answered by a document in the other
language.
"""

from dataclasses import dataclass
from typing import List, Sequence

from ai_platform.backend.domain_layer.business_logic.rag_benchmark.retrieval_sets import (
    BILINGUAL_RETRIEVAL_V1,
    Document,
    RetrievalSetError,
)


@dataclass(frozen=True)
class QAItem:
    """One question with its expected answer."""

    item_id: str
    language: str
    question: str
    expected: str
    checker: str
    relevant: Sequence[str]
    fictional: bool


@dataclass(frozen=True)
class QASet:
    """Named, versioned corpus with QA items."""

    name: str
    version: str
    documents: Sequence[Document]
    items: Sequence[QAItem]

    def __post_init__(self) -> None:
        ids = {d.doc_id for d in self.documents}
        if len(ids) != len(self.documents):
            raise RetrievalSetError("duplicate document ids")
        for item in self.items:
            if not item.relevant or set(item.relevant) - ids:
                raise RetrievalSetError(f"{item.item_id}: relevant ids not in the corpus")


_D = Document
FICTIONAL_DOCUMENTS = [
    _D("nordwind_pl", "pl", "Nordwind Logistyka to fikcyjna firma przewozowa z siedzibą w "
                            "Gdyni, założona w 2011 roku przez Halinę Wrzos."),
    _D("orion_en", "en", "Project Orion at Nordwind replaced the warehouse scanners; it was "
                         "completed on 14 March 2025, two months late."),
    _D("tariff_pl", "pl", "Abonament Nordwind Express kosztuje 49 zł miesięcznie i obejmuje "
                          "do 30 przesyłek."),
    _D("fleet_en", "en", "The Nordwind fleet has 41 trucks, of which 19 are electric and are "
                         "charged overnight in Gdynia."),
    _D("code_pl", "pl", "Kod dostępu do magazynu numer 7 firmy Nordwind to 4512 i zmienia się "
                        "co kwartał."),
    _D("support_en", "en", "Nordwind customer support answers on weekdays from 7:15 to 16:45 "
                           "at the number 58 600 12 34."),
]


# Compact positional constructor for the data table below.
def _q(item_id, language, question, expected, checker, relevant, fictional):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    return QAItem(item_id, language, question, expected, checker, [relevant], fictional)


BILINGUAL_QA_V1 = QASet(
    name="bilingual_qa", version="1",
    documents=list(BILINGUAL_RETRIEVAL_V1.documents) + FICTIONAL_DOCUMENTS,
    items=[
        _q("f1", "pl", "Kto założył firmę Nordwind Logistyka?", "Halina Wrzos|Haliny Wrzos|"
           "Halinę Wrzos|Halinie Wrzos", "phrase", "nordwind_pl", True),
        _q("f2", "pl", "Kiedy zakończono projekt Orion w firmie Nordwind?", "14 marca 2025|"
           "14 March 2025|14.03.2025", "phrase", "orion_en", True),
        _q("f3", "en", "How much does the Nordwind Express subscription cost per month?", "49",
           "numeric", "tariff_pl", True),
        _q("f4", "pl", "Ile ciężarówek elektrycznych ma Nordwind?", "19", "numeric",
           "fleet_en", True),
        _q("f5", "en", "What is the access code of Nordwind warehouse number 7?", "4512",
           "numeric", "code_pl", True),
        _q("f6", "pl", "Do której godziny działa obsługa klienta Nordwind w dni robocze?",
           "16:45|16.45", "phrase", "support_en", True),
        _q("g1", "en", "Which city is the capital of Australia?", "Canberra", "phrase",
           "canberra_pl", False),
        _q("g2", "pl", "Jakie miasto jest stolicą Polski?", "Warszawa|Warsaw|Warszawie",
           "phrase", "warsaw_en", False),
        _q("g3", "en", "Where were Polish kings crowned?", "Wawel|Kraków|Krakow|Cracow",
           "phrase", "krakow_pl", False),
        _q("g4", "pl", "Jakim protokołem zmienia się konfigurację urządzeń sieciowych?",
           "NETCONF", "phrase", "netconf_en", False),
        _q("g5", "en", "What do whales feed their young with?", "milk|mleko|mlekiem",
           "phrase", "whales_en", False),
        _q("g6", "pl", "Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy?",
           "Helm", "phrase", "helm_en", False),
    ],
)

_REGISTRY = {"bilingual_qa": BILINGUAL_QA_V1, "bilingual_qa@1": BILINGUAL_QA_V1}


def get_qa_set(name: str) -> QASet:
    """QA set by name or name@version."""
    if name not in _REGISTRY:
        raise RetrievalSetError(f"unknown QA set {name!r}; available {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_qa_sets() -> List[str]:
    """Registered names."""
    return sorted(_REGISTRY)
