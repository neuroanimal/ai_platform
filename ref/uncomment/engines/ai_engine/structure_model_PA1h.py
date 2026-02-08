import re
from common.trace_handler import TraceHandler
from common.path_handler import PathHandler
from typing import Dict, Any, Optional, List

class StructureNode:
    """Pojedynczy wezel w grafie struktury."""
    def __init__(self, name: str, node_type: str = "key"):
        self.name = name
        self.node_type = node_type  # key, index, dynamic
        self.children: Dict[str, 'StructureNode'] = {}
        self.metadata = {
            "source": None,         # helm, flat_json, or both
            "data_type": None,
            "depth": 0,
            "description": None,    # miejsce na DOC z Helma
            "is_array_element": False
        }

class StructureModel:
    """
    Buduje i przechowuje model wiedzy o strukturze parametrów.
    Implementuje logike "fuzzy match" dla sciezek dynamicznych.
    """
    def __init__(self, tracer: TraceHandler, path_handler: PathHandler):
        self.tracer = tracer
        self.path_handler = path_handler
        self.root = StructureNode("root")
        self.stats = {"nodes_created": 0, "dynamic_links": 0}

    def build_from_sources(self, helm_data: Dict, flat_json_data: Dict):
        """Integruje oba zródla danych w jeden model."""
        self.tracer.info("Budowanie modelu struktury...")

        # 1. Najpierw budujemy szkielet z Helm (SSOT)
        self._ingest_dict(helm_data, source="helm")

        # 2. Wzbogacamy o dane z Flat JSON
        for path, value in flat_json_data.items():
            self._ingest_flat_path(path, value, source="flat_json")

        self.tracer.info(f"Model zbudowany. Utworzono {self.stats['nodes_created']} wezlów.")

    def _ingest_dict(self, data: Any, parent_node: StructureNode = None, depth: int = 0, source: str = "helm"):
        """Rekurencyjnie przetwarza zagnieżdżony słownik."""
        if parent_node is None:
            parent_node = self.root

        if isinstance(data, dict):
            for key, value in data.items():
                node = self._get_or_create_node(parent_node, key, "key", depth)
                # Używamy przekazanego parametru source
                node.metadata["source"] = source
                node.metadata["data_type"] = type(value).__name__
                # Przekazujemy source dalej w rekurencji
                self._ingest_dict(value, node, depth + 1, source=source)

        elif isinstance(data, list):
            # Obsluga list w Helm - tworzymy węzeł specjalny dla elementów listy
            node = self._get_or_create_node(parent_node, "[N]", "index", depth)
            node.metadata["is_array_element"] = True
            node.metadata["source"] = source
            if data:
                # Przekazujemy source dalej w rekurencji dla elementów listy
                self._ingest_dict(data[0], node, depth + 1, source=source)

    def _ingest_flat_path(self, path: str, value: Any, source: str):
        """Wprowadza sciezke z pliku plaskiego do istniejacego modelu."""
        tokens = self.path_handler.tokenize(path)
        current = self.root

        for i, token in enumerate(tokens):
            token_val = token['value']
            # Jesli token jest dynamiczny {{...}}, szukamy pasujacego wezla lub tworzymy nowy
            if token['type'] == 'dynamic':
                self.stats["dynamic_links"] += 1

            current = self._get_or_create_node(current, token_val, token['type'], i)
            current.metadata["source"] = "both" if current.metadata["source"] == "helm" else source
            if i == len(tokens) - 1:
                current.metadata["data_type"] = type(value).__name__

    def ingest_json_parameters(self, parameters: list):
        """Procesuje listę parametrów z JSON i buduje brakujące gałęzie."""
        """Wczytuje parametry z JSON z obsługą priorytetu path/name."""
        for param in parameters:
            # Używamy pola 'name' (z kropkami) lub 'path' (z slashami)
            # Zamieniamy slashe na kropki dla spójności
            ### raw_path = param.get("name") or param.get("path").replace("/", ".").strip(".")

            path_val = param.get("path")
            name_val = param.get("name")

            # Logika priorytetu
            if path_val:
                raw_path = path_val
            elif name_val:
                raw_path = name_val
                self.tracer.warning(f"Brak pola 'path' dla parametru. Użyto 'name': {name_val}. Zgłoś potrzebę poprawy w schema JSON!")
            else:
                self.tracer.error("Pominięto parametr: brak zarówno 'path' jak i 'name'.")
                continue

            # Tokenizacja ścieżki (uwzględnia placeholdery i tablice)
            tokens = self._tokenize_complex_path(raw_path)

            # Przejście przez drzewo i budowanie węzłów
            current = self.root
            for i, token in enumerate(tokens):
                # Tutaj wchodzi special_handler, jeśli nazwa zawiera znaki specjalne
                node_type = self._determine_node_type(token)

                # Czyścimy nazwę tokena z nawiasów i śmieci
                ### clean_name = token.replace("(", "").replace(")", "")
                ### current = self._get_or_create_node(current, clean_name, n_type, i)
                current = self._get_or_create_node(current, token, node_type, i)

                # Jeśli to ostatni element (liść), dodajemy metadane z JSON
                if i == len(tokens) - 1:
                    current.metadata.update({
                        "source": "json_params",  # "source": "json",
                        "mandatory": param.get("mandatory", "no"),
                        "format": param.get("format", "unknown"),
                        "description": param.get("description", f"Status: {param.get('status')}, Release: {param.get('release')}"),
                    })

    def _determine_node_type(self, token: str) -> str:
        # Typ węzła
        """
        n_type = "key"
        if "[N]" in clean_name or re.match(r"\[\d+\]", clean_name):
            n_type = "index"
        elif "{{" in clean_name:
            n_type = "dynamic"
        return n_type
        """
        if token == "[N]": return "index"
        if "{{" in token: return "dynamic"
        if any(c in token for c in "./\\()\"'"): return "special"
        return "key"

    def _tokenize_complex_path(self, path: str) -> list:
        """
        Rozbija ścieżkę na części, pilnując, by nie rozbić placeholderów {{...}} itp.
        Zaawansowany tokenizer obsługujący grupy specjalne:
        (grupa), "grupa", 'grupa' oraz escaped versions.
        """
        # 0.Najpierw zamieniamy [2] na [N] dla uproszczenia modelu
        path = re.sub(r"\[\d+\]", ".[N]", path)

        # Rozbijamy po kropkach, ale tylko tych, które nie są wewnątrz {{ }}
        # (Uproszczony split, można go dopracować w razie problemów z grupami (x.y))
        ### return [t for t in path.split('.') if t]

# 1. Normalizacja: zamieniamy slashe na kropki (poza grupami to ryzykowne,
        # więc robimy to tylko tam, gdzie path jest formatu /root/node)
        if path.startswith('/'):
            path = path.lstrip('/').replace('/', '.')

        # 2. Regex wyłapujący segmenty:
        # Grupa 1: Zawartość w cudzysłowach (z uwzględnieniem escaped \")
        # Grupa 2: Zawartość w nawiasach (aaa.bbb/ccc)
        # Grupa 3: Standardowe nazwy między kropkami
        token_pattern = re.compile(
            r'\\?["\'](.+?)\\?["\']|'  # "..." lub '...' (również escaped)
            r'\((.+?)\)|'               # (...)
            r'([^.]+)'                  # standardowe segmenty
        )

        tokens = []
        for match in token_pattern.finditer(path):
            # Wybieramy pierwszą niepustą grupę z dopasowania
            token = next((g for g in match.groups() if g is not None), "").strip()

            if not token:
                continue

            # Unifikacja indeksów: [2] lub [N] zamieniamy na wspólny znacznik
            if re.match(r'\[\d+\]|\[N\]', token):
                tokens.append("[N]")
            else:
                tokens.append(token)

        return tokens

    def _get_or_create_node(self, parent: StructureNode, name: str, n_type: str, depth: int) -> StructureNode:
        if name not in parent.children:
            new_node = StructureNode(name, n_type)
            new_node.metadata["depth"] = depth
            parent.children[name] = new_node
            self.stats["nodes_created"] += 1
            return new_node
        return parent.children[name]

    def resolve_path_context(self, raw_path: str) -> Optional[StructureNode]:
        """
        Kluczowa funkcja: znajduje wezel w modelu dla danej sciezki,
        nawet jesli sciezka w szablonie uzywa innych nazw dla placeholderów.
        """
        tokens = self.path_handler.tokenize(raw_path)
        current = self.root

        for token in tokens:
            # 1. Próba dopasowania bezposredniego
            if token['value'] in current.children:
                current = current.children[token['value']]
            # 2. Próba dopasowania dynamicznego (jesli w modelu jest dynamiczny wezel)
            else:
                dynamic_children = [n for n in current.children.values() if n.node_type == 'dynamic']
                if dynamic_children:
                    current = dynamic_children[0]
                else:
                    return None
        return current

    def _flatten_node(self, node: StructureNode, parent_path: str = "") -> dict:
        """
        Rekurencyjnie spłaszcza drzewo węzłów do słownika ścieżek.
        Pomaga w debugowaniu i wizualizacji struktury.
        """
        items = {}
        for name, child_node in node.children.items():
            # Budujemy ścieżkę: jeśli to element listy, dodajemy [N]
            new_path = f"{parent_path}.{name}" if parent_path else name

            # Zapisujemy metadane węzła dla lepszego tracingu
            items[new_path] = child_node.metadata.get("source", "unknown")

            # Rekurencja w dół drzewa
            items.update(self._flatten_node(child_node, new_path))
        return items

    def trace_sample_paths(self, limit=50):
        """Zrzuca przykładowe ścieżki z modelu do logów dla weryfikacji."""
        self.tracer.info("Generowanie próbki ścieżek z modelu struktury...")
        # Startujemy od root.children
        ### all_paths = self._flatten_dict(self.root.children) # Używamy istniejącej funkcji
        all_paths = self._flatten_node(self.root)

        sample = list(all_paths.keys())[:limit]
        self.tracer.info(f"--- PRZYKŁADOWE ŚCIEŻKI W MODELU (Próbka {len(sample)}): ---")
        for p in sample:
            source = all_paths[p]
            self.tracer.info(f"  [PATH] ({source}): {p}")
        self.tracer.info("-----------------------------------------------------")

