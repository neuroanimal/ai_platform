"""
Retrieval test sets for comparing embedders.

A retrieval set is a small corpus plus queries with the ids of the
documents that answer them. Queries are written to *avoid* the documents'
wording where possible (paraphrase, other language), so that lexical
matching and semantic retrieval give different results - which is what
the comparison is for.

``bilingual_retrieval`` v1: 12 short documents (6 Polish, 6 English) on
economics, biology, geography and network configuration, 16 queries in
four directions: pl->pl, pl->en, en->pl, en->en.
"""

from dataclasses import dataclass
from typing import Dict, List, Sequence


class RetrievalSetError(ValueError):
    """Invalid retrieval set."""


@dataclass(frozen=True)
class Document:
    """One corpus document."""

    doc_id: str
    language: str
    text: str


@dataclass(frozen=True)
class Query:
    """A question and the ids of the documents that answer it."""

    query_id: str
    language: str
    text: str
    relevant: Sequence[str]

    def direction(self, documents: Dict[str, Document]) -> str:
        """e.g. 'pl->en' (language of the query -> of its first relevant document)."""
        return f"{self.language}->{documents[self.relevant[0]].language}"


@dataclass(frozen=True)
class RetrievalSet:
    """Named, versioned corpus with queries."""

    name: str
    version: str
    documents: Sequence[Document]
    queries: Sequence[Query]

    def __post_init__(self) -> None:
        ids = {d.doc_id for d in self.documents}
        if len(ids) != len(self.documents):
            raise RetrievalSetError("duplicate document ids")
        for query in self.queries:
            missing = set(query.relevant) - ids
            if not query.relevant or missing:
                raise RetrievalSetError(f"query {query.query_id}: bad relevant ids {missing}")

    @property
    def by_id(self) -> Dict[str, Document]:
        """Documents by id."""
        return {d.doc_id: d for d in self.documents}


_D = Document
_Q = Query

BILINGUAL_RETRIEVAL_V1 = RetrievalSet(
    name="bilingual_retrieval", version="1",
    documents=[
        _D("cpi_pl", "pl", "Inflacja CPI mierzy, jak zmieniają się ceny koszyka dóbr i usług "
                           "kupowanych przez gospodarstwa domowe."),
        _D("fx_en", "en", "The USD/PLN exchange rate is the number of Polish zloty needed to "
                          "buy one US dollar."),
        _D("rates_pl", "pl", "Rada Polityki Pieniężnej ustala stopę referencyjną, od której "
                             "zależy oprocentowanie kredytów i lokat."),
        _D("cats_en", "en", "Domestic cats are small carnivorous mammals that have lived with "
                            "humans for thousands of years."),
        _D("birds_pl", "pl", "Ptaki to kręgowce pokryte piórami, które składają jaja; wróbel i "
                             "sikora należą do ptaków."),
        _D("whales_en", "en", "Whales live in the sea, yet they breathe air and feed their "
                              "young with milk."),
        _D("canberra_pl", "pl", "Stolicą Australii jest Canberra, a nie Sydney, choć Sydney "
                                "jest większe."),
        _D("warsaw_en", "en", "Warsaw has been the capital of Poland since the late sixteenth "
                              "century and lies on the Vistula."),
        _D("krakow_pl", "pl", "Kraków był stolicą Polski przez kilka stuleci; na Wawelu "
                              "koronowano królów."),
        _D("netconf_en", "en", "NETCONF is a protocol for installing and changing the "
                               "configuration of network devices, with data modelled in YANG."),
        _D("yang_pl", "pl", "YANG to język modelowania danych konfiguracyjnych; moduł opisuje "
                            "kontenery, listy i liście."),
        _D("helm_en", "en", "Helm packages Kubernetes applications as charts whose values files "
                            "set the deployment parameters."),
    ],
    queries=[
        _Q("q01", "pl", "Jak mierzy się wzrost cen w sklepach?", ["cpi_pl"]),
        _Q("q02", "pl", "Ile złotych trzeba zapłacić za dolara?", ["fx_en"]),
        _Q("q03", "pl", "Kto decyduje o wysokości oprocentowania kredytu?", ["rates_pl"]),
        _Q("q04", "pl", "Czy kot domowy jest ssakiem?", ["cats_en"]),
        _Q("q05", "pl", "Które zwierzę morskie karmi młode mlekiem?", ["whales_en"]),
        _Q("q06", "pl", "Jakie miasto jest obecnie stolicą Polski?", ["warsaw_en"]),
        _Q("q07", "pl", "Jakim protokołem zmienia się konfigurację routera?", ["netconf_en"]),
        _Q("q08", "pl", "Czym są wykresy Helm w Kubernetesie?", ["helm_en"]),
        _Q("q09", "en", "Which city is the capital of Australia?", ["canberra_pl"]),
        _Q("q10", "en", "Who sets the reference interest rate in Poland?", ["rates_pl"]),
        _Q("q11", "en", "Is a sparrow a bird?", ["birds_pl"]),
        _Q("q12", "en", "Where were Polish kings crowned?", ["krakow_pl"]),
        _Q("q13", "en", "What language describes configuration data models?", ["yang_pl"]),
        _Q("q14", "en", "How is the change of consumer prices measured?", ["cpi_pl"]),
        _Q("q15", "en", "Do whales breathe air?", ["whales_en"]),
        _Q("q16", "en", "What tool packages applications for Kubernetes?", ["helm_en"]),
    ],
)

_REGISTRY = {"bilingual_retrieval": BILINGUAL_RETRIEVAL_V1,
             "bilingual_retrieval@1": BILINGUAL_RETRIEVAL_V1}


def get_retrieval_set(name: str) -> RetrievalSet:
    """Retrieval set by name or name@version."""
    if name not in _REGISTRY:
        raise RetrievalSetError(f"unknown retrieval set {name!r}; available {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_retrieval_sets() -> List[str]:
    """Registered names."""
    return sorted(_REGISTRY)
