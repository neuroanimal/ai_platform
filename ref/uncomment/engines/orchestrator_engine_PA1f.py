from common.trace_handler import TraceHandler
from common.path_handler import PathHandler
from common.error_handler import ErrorHandler, BaseEngineError

from engines.io_engine.helm_module import HelmModule
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
        self.helm_io = HelmModule(self.tracer)
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
            ### helm_data = self.yaml_io.read_file(self._get_path("input/structure/helm/values.yaml"))
            helm_data = self.helm_io.read_all_charts(self._get_path("input/structure/helm"))
            flat_json = {}  # self.json_io.read_file(self._get_path("input/structure/flat/params.json"))
            json_params = self.json_io.read_parameters(self._get_path("input/structure/flat/params.json"))
            template_lines = self._read_raw_template(self._get_path("input/template/values.yaml"))

            # 2. BUDOWANIE MODELU WIEDZY (Structure Model)
            self.structure_model.build_from_sources(helm_data, flat_json)  # Helm only
            self.structure_model.ingest_json_parameters(json_params)  # JSON Parameters
            self.structure_model.trace_sample_paths(50)

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
        force_uncomment_until_indent = -1

        for line in self.template_model.lines:
            content = line.raw_content

            # Jeśli jesteśmy wewnątrz bloku, który wymusiliśmy do odkomentowania
            if force_uncomment_until_indent != -1:
                if line.indent_level > force_uncomment_until_indent:
                    line.classification = "INACTIVE_DATA" # Wymuszamy status
                else:
                    force_uncomment_until_indent = -1 # Koniec bloku

            if line.classification == "INACTIVE_DATA":
                # DEBUG: Zobaczmy co skrypt próbuje dopasować
                ### print(f"DEBUG: Próba dopasowania: {line.identified_path}") 
                self.tracer.debug(f"Linia {line.line_number} | Ścieżka z szablonu: '{line.identified_path}' | Dopasowano: {line.structure_node is not None}")

                # Sprawdzamy czy sciezka tej linii istnieje w naszym modelu wiedzy
                if line.structure_node:
                    # Sukces - odkomentowujemy

                    # Jeśli ten węzeł w modelu ma dzieci (jest obiektem/listą), 
                    # wymuszamy odkomentowanie wszystkiego poniżej
                    if line.structure_node.children:
                        force_uncomment_until_indent = line.indent_level

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
                else:
                    # Tu jest pies pogrzebany - ścieżka wyliczona z szablonu 
                    # nie istnieje w modelu stworzonym z Helma.
                    self.tracer.debug(f"Nie znaleziono ścieżki w modelu: {line.identified_path}")

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

