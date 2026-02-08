from common.trace_handler import TraceHandler
from common.path_handler import PathHandler
from common.error_handler import BaseEngineError

class StructureValidator:
    """
    Odpowiada za walidacje spójnosci danych wejsciowych (Helm vs Flat JSON).
    Wykrywa kolizje, konflikty typów i brakujace galezie.
    """
    def __init__(self, tracer: TraceHandler, path_handler: PathHandler, config: dict):
        self.tracer = tracer
        self.path_handler = path_handler
        self.config = config
        self.stats = {
            "collisions_detected": 0,
            "type_mismatches": 0,
            "missing_in_helm": 0
        }

    def validate_input_consistency(self, helm_data: dict, flat_json_data: dict):
        """
        Porównuje strukture Helm (SSOT) z plaskim plikiem JSON.
        Szuka parametrów w JSON, których nie ma w Helm, oraz sprawdza zgodnosc typów.
        """
        self.tracer.info("Rozpoczynanie walidacji spójnosci struktur wejsciowych...")

        # Splaszczamy Helm do listy sciezek dla latwiejszego porównania
        helm_paths = self._flatten_dict(helm_data)

        for json_path, json_value in flat_json_data.items():
            # 1. Normalizacja i tokenizacja sciezki z JSON
            tokens = self.path_handler.tokenize(json_path)
            normalized_path = self.path_handler.join_tokens(tokens)

            # 2. Sprawdzenie czy sciezka istnieje w SSOT (Helm)
            if normalized_path not in helm_paths:
                self.tracer.warning(f"Parametr '{json_path}' obecny w JSON, ale brak go w Helm (SSOT).")
                self.stats["missing_in_helm"] += 1
                continue

            # 3. Walidacja typu (jesli SSOT ma przypisany typ)
            helm_value = helm_paths[normalized_path]
            if not self._compare_types(helm_value, json_value):
                self.tracer.warning(
                    f"Konflikt typów dla '{normalized_path}': "
                    f"Helm={type(helm_value).__name__}, JSON={type(json_value).__name__}"
                )
                self.stats["type_mismatches"] += 1
                self.stats["collisions_detected"] += 1

        self.tracer.info(f"Walidacja zakonczona. Wykryto {self.stats['collisions_detected']} kolizji.")

    def _flatten_dict(self, d: dict, parent_path: str = "") -> dict:
        """Pomocnicza funkcja splaszczajaca zagniezdzony slownik do formatu sciezek."""
        items = {}
        for k, v in d.items():
            new_path = f"{parent_path}.{k}" if parent_path else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_path))
            else:
                items[new_path] = v
        return items

    def _compare_types(self, val1: Any, val2: Any) -> bool:
        """Porównuje typy danych, biorac pod uwage 'ulomnosci' (np. stringi udajace inty)."""
        if val1 is None or val2 is None:
            return True # Dopuszczamy null zgodnie z Twoim zalozeniem

        type1 = type(val1)
        type2 = type(val2)

        if type1 == type2:
            return True

        # Specyficzny edge-case: liczby jako stringi
        if isinstance(val1, (int, float)) and isinstance(val2, str):
            try:
                float(val2)
                return True
            except ValueError:
                return False

        return False

    def get_summary(self) -> dict:
        return self.stats