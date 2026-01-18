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