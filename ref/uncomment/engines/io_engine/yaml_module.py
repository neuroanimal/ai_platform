from ruamel.yaml import YAML
from common.trace_handler import TraceHandler
from common.error_handler import BaseEngineError
import io

class YAMLModule:
    """
    Modul obslugi plików YAML w ramach IO Engine.
    Zapewnia zachowanie komentarzy i struktury dzieki ruamel.yaml.
    """
    def __init__(self, tracer: TraceHandler):
        self.tracer = tracer
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        # Slownik do przechowywania statystyk modulu
        self.stats = {
            "files_read": 0,
            "files_written": 0,
            "preprocessing_hits": 0
        }

    def read_file(self, file_path: str) -> dict:
        """Odczytuje plik YAML do kolekcji (CommentedMap)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. Preprocessing
            processed_content = self._preprocessing(content)

            # 2. Load
            data = self.yaml.load(processed_content)
            self.stats["files_read"] += 1
            self.tracer.info(f"Pomyslnie wczytano YAML: {file_path}")
            return data
        except Exception as e:
            self.tracer.logger.error(f"Blad odczytu YAML {file_path}: {str(e)}")
            raise BaseEngineError(f"Nie udalo sie wczytac YAML: {str(e)}")

    def write_file(self, data: dict, output_path: str):
        """Zapisuje kolekcje do pliku YAML z uwzglednieniem postprocessingu."""
        try:
            # Uzywamy buffer, aby móc wykonac postprocessing na stringu przed zapisem
            stream = io.StringIO()
            self.yaml.dump(data, stream)
            content = stream.getvalue()

            # 3. Postprocessing
            final_content = self._postprocessing(content)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)

            self.stats["files_written"] += 1
            self.tracer.info(f"Pomyslnie zapisano YAML: {output_path}")
        except Exception as e:
            raise BaseEngineError(f"Blad zapisu YAML {output_path}: {str(e)}")

    def _preprocessing(self, content: str) -> str:
        """
        Podmodul preprocessing: statyczna podmiana/czyszczenie input stringa.
        Tu mozemy dodac regexy usuwajace niestandardowe tagi przed parsowaniem.
        """
        original_content = content
        # Przyklad: usuwanie specyficznych dla Helm znaczników, które psuja YAML
        # content = content.replace("{{-", "# {{-")

        if content != original_content:
            self.stats["preprocessing_hits"] += 1
            self.tracer.debug("Wykonano preprocessing na tresci YAML.")
        return content

    def _postprocessing(self, content: str) -> str:
        """
        Podmodul postprocessing: finalne szlify przed zapisem na dysk.
        """
        # Przyklad: wymuszanie pustej linii na koncu pliku
        if not content.endswith('\n'):
            content += '\n'
        return content

    def get_summary(self) -> dict:
        """Zwraca podsumowanie pracy modulu (YAML File Summary)."""
        return self.stats