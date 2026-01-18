import re
from typing import List, Optional
from common.trace_handler import TraceHandler
from common.path_handler import PathHandler
from engines.ai_engine.structure_model import StructureModel

class TemplateLine:
    """Reprezentuje pojedyncza linie szablonu wraz z jej klasyfikacja i kontekstem."""
    def __init__(self, raw_content: str, line_no: int):
        self.raw_content = raw_content
        self.line_no = line_no
        self.indent_level = len(raw_content) - len(raw_content.lstrip())
        self.classification = None  # DOC, CONSTRAINT, ACTIVE_DATA, INACTIVE_DATA
        self.identified_path = None
        self.structure_node = None
        self.confidence = 1.0  # 1.0 dla regul, <1.0 dla AI

class TemplateModel:
    """
    Analizuje szablon YAML, klasyfikuje linie i wiaze je z modelem struktury.
    Dziala w trybie hybrydowym: Rule-Based -> AI-Augmented.
    """
    def __init__(self, tracer: TraceHandler, path_handler: PathHandler, structure_model: StructureModel):
        self.tracer = tracer
        self.path_handler = path_handler
        self.structure_model = structure_model
        self.lines: List[TemplateLine] = []
        
        # Reguly RBMT (Regex)
        self.rules = {
            "data_pattern": re.compile(r'^\s*#?\s*([a-zA-Z0-9_\-\.]+)\s*:\s*(.*)'),
            "constraint_keywords": ["mandatory", "must", "do not", "readonly", "obsolete"],
            "comment_marker": "#"
        }

    def process_template(self, raw_lines: List[str]):
        """Glówna petla procesujaca szablon."""
        self.tracer.info("Rozpoczynanie klasyfikacji linii szablonu (Metoda RBMT)...")
        
        current_stack = []  # Do sledzenia hierarchii podczas czytania

        for i, raw_content in enumerate(raw_lines):
            line = TemplateLine(raw_content, i + 1)
            self._classify_line(line)
            
            # Jesli to dane (aktywne lub nie), próbujemy wyznaczyc sciezke
            if line.classification in ["ACTIVE_DATA", "INACTIVE_DATA"]:
                self._resolve_line_path(line, current_stack)
            
            self.lines.append(line)

    def _classify_line(self, line: TemplateLine):
        """Pierwsza warstwa: Rule-Based Classification."""
        stripped = line.raw_content.strip()
        if not stripped:
            line.classification = "EMPTY"
            return

        # Poprawiony regex: lepiej radzi sobie z zagnieżdżonymi hashami i spacjami
        # Grupa 1: Klucz, Grupa 2: Wartość
        regex = r'^([a-zA-Z0-9_\-\.]+)\s*:\s*(.*)'
        # Próba wyciągnięcia klucza i wartości (nawet zza hasha)
        content_for_check = stripped.lstrip('#').strip()
        data_match = re.search(regex, content_for_check)

        # 1. Sprawdzanie czy to ACTIVE_DATA (brak hasha na poczatku, pasuje do klucz:wartosc)
        if not stripped.startswith(self.rules["comment_marker"]):
            ### if self.rules["data_pattern"].match(stripped):
            # Linia aktywna
            if data_match:
                line.classification = "ACTIVE_DATA"
                ### return
            else:
                line.classification = "DOCUMENTATION" # Może to być np. "-" w liście
            return
        # 2. Sprawdzanie czy to INACTIVE_DATA (jest hash, ale struktura to klucz:wartosc)
        ###else:

        # Linia zakomentowana - tu decydujemy czy to Dane czy Dokumentacja
        # Jeśli jest hash, sprawdzamy czy to dane czy tekst
        ### content_after_hash = stripped[1:].strip()
        ### if self.rules["data_pattern"].match(content_after_hash):
        if data_match:
            potential_key = data_match.group(1)

            # RBMT: Jeśli klucz jest na liście ignorowanych lub zbyt długi -> DOC
            if potential_path := self._guess_path(line, potential_key):
                # Sprawdzamy w modelu, czy taki klucz w ogóle istnieje w produkcie
                if self.structure_model.resolve_path_context(potential_path):
                    line.classification = "INACTIVE_DATA"
                    return

            # Dodatkowy bezpiecznik: jeśli po hashu jest dużo tekstu bez struktury, to DOC
            if len(potential_key) < 50: # Klucze YAML rzadko są aż tak długie
                line.classification = "INACTIVE_DATA"
                return
        
        # 3. Sprawdzanie CONSTRAINT (slowa kluczowe w komentarzu)
        # Jeśli nie przeszło walidacji jako dane, sprawdź CONSTRAINT
        if any(k in stripped.lower() for k in self.rules["constraint_keywords"]):
            line.classification = "CONSTRAINT"
        # 4. Jesli nic nie pasuje, to DOCUMENTATION
        else:
            line.classification = "DOCUMENTATION"
        return

    def _guess_path(self, line: TemplateLine, key: str) -> str:
        """Pomocnicza funkcja do budowania ścieżki 'na próbę'."""
        # Implementacja zależy od Twojego mechanizmu stosu (stack)
        # Na potrzeby testu może zwracać po prostu klucz
        return key

    def _resolve_line_path(self, line: TemplateLine, stack: List[dict]):
        """Wiaze linie z modelem struktury na podstawie wciec (Logic of Indentation)."""
        match = self.rules["data_pattern"].search(line.raw_content)
        if not match: return

        key = match.group(1)
        
        # Zarzadzanie stosem wciec (indentation-based tree traversal)
        while stack and stack[-1]['indent'] >= line.indent_level:
            stack.pop()
        
        parent_path = stack[-1]['path'] if stack else ""
        current_path = f"{parent_path}.{key}" if parent_path else key
        
        line.identified_path = current_path
        line.structure_node = self.structure_model.resolve_path_context(current_path)
        
        stack.append({'indent': line.indent_level, 'path': current_path})

    def get_inactive_data_lines(self) -> List[TemplateLine]:
        """Zwraca tylko te linie, które sa kandydatami do odkomentowania."""
        return [l for l in self.lines if l.classification == "INACTIVE_DATA"]

