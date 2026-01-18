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

        # 1. Sprawdzanie czy to ACTIVE_DATA (brak hasha na poczatku, pasuje do klucz:wartosc)
        if not stripped.startswith(self.rules["comment_marker"]):
            if self.rules["data_pattern"].match(stripped):
                line.classification = "ACTIVE_DATA"
                return

        # 2. Sprawdzanie czy to INACTIVE_DATA (jest hash, ale struktura to klucz:wartosc)
        if stripped.startswith(self.rules["comment_marker"]):
            content_after_hash = stripped[1:].strip()
            if self.rules["data_pattern"].match(content_after_hash):
                line.classification = "INACTIVE_DATA"
                return
            
            # 3. Sprawdzanie CONSTRAINT (slowa kluczowe w komentarzu)
            if any(k in stripped.lower() for k in self.rules["constraint_keywords"]):
                line.classification = "CONSTRAINT"
                return

            # 4. Jesli nic nie pasuje, to DOCUMENTATION
            line.classification = "DOCUMENTATION"

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