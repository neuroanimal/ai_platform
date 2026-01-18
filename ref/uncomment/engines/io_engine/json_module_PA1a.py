import json
from common.trace_handler import TraceHandler
from common.error_handler import BaseEngineError

class JSONModule:
    """
    Modul obslugi plaskich plików JSON w ramach IO Engine.
    Specjalizuje sie w wczytywaniu metadanych i parametrów (Flat JSON).
    """
    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.stats = {
            "files_read": 0,
            "validation_warnings": 0,
            "preprocessed_keys": 0
        }

    def read_file(self, file_path: str) -> dict:
        """Odczytuje plaski plik JSON i normalizuje go do slownika."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. Preprocessing (np. usuwanie komentarzy z JSON, jesli wystepuja)
            processed_content = self._preprocessing(content)
            
            data = json.loads(processed_content)
            
            # 2. Wstepna analiza jakosci (bez blokowania procesu)
            self._analyze_quality(data, file_path)
            
            self.stats["files_read"] += 1
            self.tracer.info(f"Pomyslnie wczytano JSON: {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            self.tracer.logger.error(f"Blad skladni JSON w {file_path}: {str(e)}")
            raise BaseEngineError(f"Niepoprawny format JSON: {str(e)}")
        except Exception as e:
            raise BaseEngineError(f"Blad krytyczny odczytu JSON: {str(e)}")

    def write_file(self, data: dict, output_path: str):
        """Zapisuje dane do pliku JSON (np. statystyki lub przetworzone mapowania)."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.stats["files_read"] += 1 
        except Exception as e:
            raise BaseEngineError(f"Blad zapisu JSON {output_path}: {str(e)}")

    def _preprocessing(self, content: str) -> str:
        """Statyczna obróbka stringa JSON przed parsowaniem."""
        # Przykladowo: usuwanie spacji z konców linii lub naprawa urwanych przecinków
        return content.strip()

    def _analyze_quality(self, data: dict, file_name: str):
        """
        Wstepna heurystyka wykrywania bledów, o których wspominales 
        (np. puste wartosci, podejrzane formaty).
        """
        if not isinstance(data, (dict, list)):
            self.tracer.warning(f"Plik {file_name} nie zawiera obiektu ani listy!")
            return

        # Jesli to plaski slownik sciezek
        if isinstance(data, dict):
            for key, value in data.items():
                if value is None:
                    self.tracer.debug(f"Pusta wartosc dla klucza: {key}")
                    self.stats["validation_warnings"] += 1
                
                # Wykrywanie "ulomnych" typów (np. string "true" zamiast boolean)
                if isinstance(value, str) and value.lower() in ['true', 'false']:
                    self.tracer.debug(f"Klucz {key} zawiera boolean jako string.")
                    self.stats["validation_warnings"] += 1

    def get_summary(self) -> dict:
        return self.stats