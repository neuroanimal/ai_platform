import re
from typing import List, Dict, Optional
from common.trace_handler import TraceHandler
from common.path_handler import PathHandler
from engines.ai_engine.structure_model import StructureModel

class TemplateLine:
    """Reprezentuje pojedyncza linie szablonu wraz z jej klasyfikacja i kontekstem."""
    def __init__(self, raw_content: str, line_no: int):
        self.raw_content = raw_content
        self.line_no = line_no
        self.line_number = line_no
        self.indent_level = self._calculate_indent(raw_content)
        self.classification = None  # DOC, CONSTRAINT, ACTIVE_DATA, INACTIVE_DATA
        self.identified_path = None
        self.structure_node = None
        self.confidence = 1.0  # 1.0 dla regul, <1.0 dla AI

    # Przykład poprawnego liczenia wcięcia dla linii zakomentowanych
    def _calculate_indent(self, line_str):
        # Liczymy spacje od początku, ignorując czy tam jest # czy nie
        return len(line_str) - len(line_str.lstrip(' '))


class TemplateModel:
    """
    Analizuje szablon YAML, klasyfikuje linie i wiaze je z modelem struktury.
    Dziala w trybie hybrydowym: Rule-Based -> AI-Augmented.
    """
    # def __init__(self, structure_model, tracer):
    def __init__(self, tracer: TraceHandler, path_handler: PathHandler, structure_model: StructureModel):
        self.tracer = tracer
        self.path_handler = path_handler
        self.structure_model = structure_model
        self.lines: List[TemplateLine] = []

        # Stos kontekstu: przechowuje słowniki {'indent': int, 'path': str}
        self.context_stack = [] 

        # Reguly RBMT (Regex)
        self.rules = {
            "data_pattern": re.compile(r'^\s*#?\s*([a-zA-Z0-9_\-\.]+)\s*:\s*(.*)'),
            "constraint_keywords": ["mandatory", "must", "do not", "readonly", "obsolete"],
            "comment_marker": "#"
        }

    def process_template(self, raw_lines: List[str]):
        """Glówna petla procesujaca szablon."""
        self.tracer.info("Rozpoczynanie klasyfikacji linii szablonu (Metoda RBMT)...")
        
        """Główna pętla analizująca i procesująca szablon linia po linii."""
        self.context_stack = [] # Reset stosu przed nowym plikiem
        ### current_stack = []  # Do sledzenia hierarchii podczas czytania

        for idx, raw_content in enumerate(raw_lines):
            # line = TemplateLine(idx, raw_content)
            line = TemplateLine(raw_content, idx + 1)

            # 1. Klasyfikacja wstępna (RBMT)
            self._classify_line(line)

            # 2. Budowanie ścieżki i powiązanie z modelem (Smart Context Tracker)
            # Jeśli to dane (aktywne lub nie), próbujemy wyznaczyć ścieżkę
            if line.classification in ["ACTIVE_DATA", "INACTIVE_DATA"]:
                ### self._resolve_line_path(line, current_stack)
                ### self._resolve_smart_path(line)
                ### self._resolve_smart_path_new(line)
                self._resolve_with_backtracking(line)

            self.lines.append(line)

    def _classify_line(self, line: TemplateLine):
        """Pierwsza warstwa: Rule-Based Classification."""
        stripped = line.raw_content.strip()
        if not stripped:
            line.classification = "EMPTY"
            return

        # Poprawiony regex: lepiej radzi sobie z zagnieżdżonymi hashami i spacjami
        # Rozszerzony regex dla kluczy i wartości z placeholderami
        # RZEKOMO obsługuje: key: {{true|false}} oraz key: "zwykła wartość"
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
            value_part = data_match.group(2).strip()

            # Jeśli wartość to placeholder typu {{...}}, oznaczamy to jako wysoką pewność danych
            if value_part.startswith('{{') and value_part.endswith('}}'):
                line.classification = "INACTIVE_DATA"
                line.confidence = 1.0

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
        """
        Wiaze linie z modelem struktury na podstawie wciec (Logic of Indentation).
        Udoskonalone śledzenie kontekstu. 
        Obsługuje listy i dynamiczne poziomy wcięć.
        """

        ### match = self.rules["data_pattern"].search(line.raw_content)
        ### if not match: return
        ### key = match.group(1)

        # Czyścimy linię z komentarzy i białych znaków, by znaleźć klucz
        stripped_content = line.raw_content.lstrip().lstrip('#').strip()
        
        # Obsługa elementu listy: "- key: value" lub "- value"
        is_list_item = stripped_content.startswith('-')
        clean_key_match = re.search(r'([a-zA-Z0-9_\-\.]+)\s*:', stripped_content.lstrip('- '))
        
        key = clean_key_match.group(1) if clean_key_match else (None if not is_list_item else "[N]")
        if not key: return

        # Zarządzanie stosem wcięć - na podstawie wcięć (indent_level) - indentation-based tree traversal
        while stack and stack[-1]['indent'] >= line.indent_level:
            stack.pop()

        parent_path = stack[-1]['path'] if stack else ""
        
        # Jeśli jesteśmy w liście, dodajemy marker [N] do ścieżki
        current_path = f"{parent_path}.{key}" if parent_path else key
        
        line.identified_path = current_path
        # Próba dopasowania w StructureModel (z uwzględnieniem fuzzy match dla [N])
        line.structure_node = self.structure_model.resolve_path_context(current_path)
        
        # Zapamiętujemy ten poziom na stosie
        stack.append({'indent': line.indent_level, 'path': current_path})

    def _resolve_smart_path(self, line: TemplateLine):
        """
        Zarządza stosem wcięć i buduje pełną ścieżkę hierarchiczną.
        Obsługuje również elementy list (zaczynające się od '-').
        """
        stripped = line.raw_content.lstrip().lstrip('#').strip()
        
        # Wyciągamy klucz: "key:", "- key:" lub "- value" (traktowane jako [N])
        key_match = re.search(r'^([a-zA-Z0-9_\-\.]+)\s*:', stripped.lstrip('- '))
        
        if key_match:
            current_key = key_match.group(1)
        elif stripped.startswith('-'):
            current_key = "[N]" # Element listy bezkluczowej
        else:
            return # Nie jest to linia z danymi, którą chcemy śledzić w ścieżce

        # Zdejmujemy ze stosu wszystko, co ma większe lub równe wcięcie
        # (Wychodzimy z głębszych poziomów struktury)
        while self.context_stack and self.context_stack[-1]['indent'] >= line.indent_level:
            self.context_stack.pop()

        # Budujemy pełną ścieżkę na podstawie rodzica ze stosu
        parent_path = self.context_stack[-1]['path'] if self.context_stack else ""
        
        # Obsługa specyfiki list w ścieżkach
        if stripped.startswith('-') and not current_key == "[N]":
            # Przypadek: "- key: value" -> to jest element listy, który sam jest obiektem
            full_path = f"{parent_path}.[N].{current_key}" if parent_path else f"[N].{current_key}"
        else:
            full_path = f"{parent_path}.{current_key}" if parent_path else current_key

        # Kluczowa zmiana: upewnij się, że nie wysyłamy kropek na początku/końcu

        # Czyszczenie ścieżki z ewentualnych podwójnych kropek
        full_path = full_path.strip('.')

        # DEBUG: To pozwoli Ci porównać co idzie z szablonu, a co wpisywałeś w verify_model
        self.tracer.debug(f"Szukanie w modelu: {full_path}")

        line.identified_path = full_path

        # PRÓBA POWIĄZANIA Z MODELEM STRUKTURY
        line.structure_node = self.structure_model.resolve_path_context(full_path)
        
        if line.structure_node:
            self.tracer.debug(f"SUKCES: Dopasowano {full_path}")
        
        # Dodajemy obecny poziom na stos dla przyszłych linii (dzieci)
        self.context_stack.append({
            'indent': line.indent_level,
            'path': full_path
        })

    def _resolve_smart_path_new(self, line: TemplateLine):
        # 1. Dokładne czyszczenie treści, by wyciągnąć klucz
        # Usuwamy komentarze, białe znaki na początku i końcowe dwukropki
        raw_clean = line.raw_content.strip()
        content_no_comment = raw_clean.lstrip('#').strip()
        
        # Wyciągamy klucz przed dwukropkiem
        key_match = re.search(r'^([a-zA-Z0-9_\-\.]+)\s*:', content_no_comment.lstrip('- '))
        
        if key_match:
            current_key = key_match.group(1)
        elif content_no_comment.startswith('-'):
            current_key = "[N]"
        else:
            return

        # 2. LOGIKA STOSU (Kluczowa poprawka)
        # Zdejmujemy ze stosu, jeśli obecne wcięcie jest MNIEJSZE lub RÓWNE
        # Musimy upewnić się, że indent_level jest liczony od początku linii (łącznie ze spacjami przed #)
        while self.context_stack and self.context_stack[-1]['indent'] >= line.indent_level:
            self.context_stack.pop()

        parent_path = self.context_stack[-1]['path'] if self.context_stack else ""
        
        # Budujemy ścieżkę
        if content_no_comment.startswith('-') and current_key != "[N]":
             # Element listy będący obiektem: - key: val
             full_path = f"{parent_path}.[N].{current_key}" if parent_path else f"[N].{current_key}"
        else:
             full_path = f"{parent_path}.{current_key}" if parent_path else current_key

        full_path = full_path.strip('.')
        line.identified_path = full_path

        # 3. PRÓBA DOPASOWANIA
        line.structure_node = self.structure_model.resolve_path_context(full_path)
        
        # Jeśli dopasowano, dodajemy do stosu dla dzieci
        self.context_stack.append({
            'indent': line.indent_level,
            'path': full_path
        })

    def get_inactive_data_lines(self) -> List[TemplateLine]:
        """Zwraca tylko te linie, które sa kandydatami do odkomentowania."""
        return [l for l in self.lines if l.classification == "INACTIVE_DATA"]

    def _resolve_with_backtracking(self, line: TemplateLine):
        content = line.raw_content.lstrip().lstrip('#').strip()
        key_match = re.search(r'^([a-zA-Z0-9_\-\.]+)\s*:', content.lstrip('- '))
        current_key = key_match.group(1) if key_match else ("[N]" if content.startswith('-') else None)

        if not current_key:
            return

        # PRÓBA KOTWICZENIA: Przeszukujemy stos od końca w górę
        best_parent_node = None
        new_stack_depth = -1

        # Szukamy w StructureModel, który z przodków na stosie 'zna' ten klucz
        for depth in range(len(self.context_stack) - 1, -1, -1):
            parent_node = self.context_stack[depth]['node']
            
            # resolve_path_context musi teraz umieć sprawdzić bezpośrednie dziecko
            if current_key in parent_node.children or "[N]" in parent_node.children:
                best_parent_node = parent_node
                new_stack_depth = depth
                break

        if best_parent_node:
            # Sukces! Znaleźliśmy 'prawdziwego' rodzica w modelu.
            # Skracamy stos do poziomu tego rodzica (automatyczna korekta wcięć!)
            self.context_stack = self.context_stack[:new_stack_depth + 1]
            
            # Pobieramy węzeł dziecka
            if current_key in best_parent_node.children:
                line.structure_node = best_parent_node.children[current_key]
            else:
                line.structure_node = best_parent_node.children["[N]"]

            parent_path = self.context_stack[-1]['path']
            line.identified_path = f"{parent_path}.{current_key}".strip('.')
            
            # Dodajemy nowy węzeł na stos
            self.context_stack.append({
                'indent': line.indent_level, # Zachowujemy dla orientacji, ale nie ufamy mu w 100%
                'path': line.identified_path,
                'node': line.structure_node
            })

