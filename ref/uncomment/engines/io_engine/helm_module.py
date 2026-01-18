import tarfile
import yaml
import re
import os
from io import BytesIO
from common.trace_handler import TraceHandler

class HelmModule:
    """
    Specjalistyczny modul do obslugi rozproszonych i spakowanych Helm Charts.
    Obsluguje archiwa .tgz i automatycznie mapuje subcharty na hierarchie YAML.
    """
    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.stats = {"archives_processed": 0, "values_files_found": 0, "skipped_files": 0}
        # Regex do wykrywania i usuwania tagów Helm {{ ... }}
        self.helm_tag_regex = re.compile(r'\{\{.*?\}\}', re.DOTALL)

    def read_all_charts(self, helm_dir: str) -> dict:
        """Przeszukuje katalog i scala wszystkie values.yaml z wielu archiwów .tgz."""
        aggregated_data = {}
        
        if not os.path.exists(helm_dir):
            self.tracer.warning(f"Katalog Helm nie istnieje: {helm_dir}")
            return aggregated_data

        for filename in os.listdir(helm_dir):
            if filename.endswith(".tgz"):
                archive_path = os.path.join(helm_dir, filename)
                self.tracer.info(f"Przetwarzanie archiwum Helm: {filename}")
                chart_data = self._process_tgz(archive_path)
                # Glebokie scalanie (deep merge) danych z archiwum do glównego worka
                self._deep_merge(aggregated_data, chart_data)
                self.stats["archives_processed"] += 1
        
        return aggregated_data

    def _process_tgz(self, tgz_path: str) -> dict:
        """Wyciaga dane z jednego archiwu .tgz, mapujac subcharty na klucze."""
        chart_root_data = {}
        
        with tarfile.open(tgz_path, "r:gz") as tar:
            for member in tar.getmembers():
                # Interesują nas TYLKO pliki values.yaml (unikamy templates/ i helpers!)
                if member.name.endswith("values.yaml") and member.isfile():
                    f = tar.extractfile(member)
                    if not f: continue
                    
                    raw_content = f.read().decode('utf-8', errors='ignore')
                    
                    # 1. CZYSZCZENIE: Usuwamy tagi Helma przed parsowaniem YAML
                    sanitized_content = self._sanitize_helm_content(raw_content)
                    
                    try:
                        # 2. PARSOWANIE z obsługą błędów
                        # Wyznaczamy "sciezke kluczy" na podstawie struktury katalogów
                        # Np. 'mychart/charts/logging/values.yaml' -> ['logging']
                        content = yaml.safe_load(sanitized_content)
                        if not content: continue
                        
                        self.stats["values_files_found"] += 1
                        key_path = self._infer_key_path(member.name)
                        
                        if not key_path:
                            self._deep_merge(chart_root_data, content)
                        else:
                            self._nest_data(chart_root_data, key_path, content)
                            
                    except yaml.YAMLError as e:
                        self.tracer.warning(f"Pominięto plik {member.name} w {os.path.basename(tgz_path)} - Błąd składni YAML (prawdopodobnie złożony template).")
                        self.stats["skipped_files"] += 1
                        continue
                            
        return chart_root_data

    def _sanitize_helm_content(self, content: str) -> str:
        """
        Zamienia tagi {{ ... }} na bezpieczne komentarze lub je usuwa,
        aby linter YAML nie zgłaszał błędów.
        """
        # Zamieniamy {{ ... }} na # [HELM_TAG]... , aby zachować strukturę linii
        return self.helm_tag_regex.sub("# [HELM_TAG]", content)

    def _infer_key_path(self, internal_path: str) -> list:
        """
        Analizuje sciezke wewnatrz tar i zwraca liste subchartów.
        Przyklad: 'abc/charts/def/charts/ghi/values.yaml' -> ['def', 'ghi']
        """
        parts = internal_path.split('/')
        keys = []
        for i, part in enumerate(parts):
            if part == "charts" and i + 1 < len(parts):
                keys.append(parts[i+1])
        return keys

    def _nest_data(self, root: dict, keys: list, data: dict):
        """Wsadza slownik data gleboko pod klucze z listy keys."""
        for key in keys[:-1]:
            root = root.setdefault(key, {})
        if keys:
            last_key = keys[-1]
            if last_key in root:
                self._deep_merge(root[last_key], data)
            else:
                root[last_key] = data

    def _deep_merge(self, base: dict, source: dict):
        """Rekurencyjne scalanie dwóch slowników."""
        for key, value in source.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

