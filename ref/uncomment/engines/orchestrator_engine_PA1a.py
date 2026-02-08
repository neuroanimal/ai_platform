from common.trace_handler import TraceHandler
from common.path_handler import PathHandler
from common.error_handler import ErrorHandler, BaseEngineError

from engines.io_engine.yaml_module import YAMLModule
from engines.io_engine.json_module import JSONModule
from engines.ai_engine.structure_model import StructureModel
from engines.ai_engine.template_model import TemplateModel

class OrchestratorEngine:
    """
    Master Engine zarzadzajacy przeplywem danych miedzy modulami.
    Realizuje petle: Read -> Model -> Process -> Fix -> Write.
    """
    def __init__(self, product: str, version: str, config: dict):
        self.product = product
        self.version = version
        self.config = config

        # Inicjalizacja Handlerów
        self.tracer = TraceHandler(product, version, "Orchestrator")
        self.path_handler = PathHandler()  # (config_mapping=self.config)

        # Inicjalizacja Modulów IO
        self.yaml_io = YAMLModule(self.tracer)
        self.json_io = JSONModule(self.tracer)

        # Inicjalizacja Silników AI
        self.structure_model = StructureModel(self.tracer, self.path_handler)
        self.template_model = TemplateModel(self.tracer, self.path_handler, self.structure_model)

    def run_uncomment_process(self):
        """Glówny proces end-to-end."""
        try:
            self.tracer.info(f"--- START PROCESU: {self.product} v{self.version} ---")

            # 1. ODCZYT DANYCH WEJSCIOWYCH
            helm_data = self.yaml_io.read_file(self._get_path("input/structure/helm/values.yaml"))
            flat_json = self.json_io.read_file(self._get_path("input/structure/flat/params.json"))
            template_lines = self._read_raw_template(self._get_path("input/template/values.yaml"))

            # 2. BUDOWANIE MODELU WIEDZY (Structure Model)
            self.structure_model.build_from_sources(helm_data, flat_json)

            # 3. ANALIZA I KLASYFIKACJA SZABLONU (Template Model)
            self.template_model.process_template(template_lines)

            # 4. PETLA DECYZYJNA (PROCES OD-KOMENTOWYWANIA)
            processed_lines = self._execute_uncomment_logic()

            # 5. ZAPIS WYNIKU (Pierwsza iteracja)
            self._write_output_template(processed_lines)

            self.tracer.info("--- PROCES ZAKONCZONY SUKCESEM ---")

        except Exception as e:
            ErrorHandler.handle(e, self.tracer)

    def _execute_uncomment_logic(self) -> list:
        """
        Logika decyzyjna: Dla kazdej linii INACTIVE_DATA sprawdza,
        czy powinna zostac odkomentowana na podstawie modelu struktury.
        """
        final_lines = []
        uncommented_count = 0

        for line in self.template_model.lines:
            content = line.raw_content

            if line.classification == "INACTIVE_DATA":
                # Sprawdzamy czy sciezka tej linii istnieje w naszym modelu wiedzy
                if line.structure_node:
                    # DECYZJA: Jesli model zna ten parametr, odkomentowujemy go
                    # Tutaj wyliczamy tez odpowiednie wciecie
                    target_indent = line.structure_node.metadata['depth'] * 2
                    clean_content = line.raw_content.strip().lstrip('#').strip()

                    content = f"{' ' * target_indent}{clean_content}\n"
                    uncommented_count += 1
                    self.tracer.trace_decision(
                        step="uncomment",
                        reason=f"Found in StructureModel at path: {line.identified_path}"
                    )

            final_lines.append(content)

        self.tracer.info(f"Odkomentowano {uncommented_count} linii na podstawie modelu.")
        return final_lines

    def _get_path(self, sub_path: str) -> str:
        """Pomocnik do budowania sciezek zgodnych z Twoja struktura."""
        return f"data/{self.product}/{self.version}/{sub_path}"

    def _read_raw_template(self, path: str) -> list:
        with open(path, 'r', encoding='utf-8') as f:
            return f.readlines()

    def _write_output_template(self, lines: list):
        out_path = self._get_path("output/template/uncommented_values.yaml")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

