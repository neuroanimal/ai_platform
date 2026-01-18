import re

# SYMULACJA MODELU STRUKTURY (zamiast StructureModel)
# Tu wpisujemy to, co wiemy z Helmów i JSONa
MODEL_KNOWLEDGE = {
    "something": ["niceObject", "otherParam"],
    "niceObject": ["child111", "child222"],
    "abecadlo": ["abc.def.ghi/jkl"],
    "root": ["something", "abecadlo", "otherNode"]
}

def simulate_backtracking_logic(yaml_lines):
    # Stos przechowuje słowniki: {'name': str, 'path': str}
    # Zaczynamy od wirtualnego korzenia 'root'
    stack = [{'name': 'root', 'path': ''}]
    
    print(f"{'LINE':<35} | {'DECISION':<15} | {'RESOLVED PATH'}")
    print("-" * 80)
    
    for raw_line in yaml_lines:
        if not raw_line.strip(): continue
        
        # 1. Wyciągamy klucz niezależnie od śmieci
        content = raw_line.lstrip().lstrip('#').strip()
        key_match = re.search(r'^([a-zA-Z0-9_\-\./]+)\s*:', content.lstrip('- '))
        if not key_match: continue
        current_key = key_match.group(1)

        # 2. BACKTRACKING: Szukamy rodzica na stosie od góry do dołu
        found_parent = False
        # Przeszukujemy stos od najświeższego elementu do korzenia
        for i in range(len(stack) - 1, -1, -1):
            potential_parent = stack[i]['name']
            
            # Sprawdzamy w naszej "bazie wiedzy", czy ten rodzic zna ten klucz
            if potential_parent in MODEL_KNOWLEDGE and current_key in MODEL_KNOWLEDGE[potential_parent]:
                # Znaleźliśmy! Skracamy stos do tego poziomu (wyrzucamy błędnych "braci")
                stack = stack[:i + 1]
                
                parent_path = stack[-1]['path']
                full_path = f"{parent_path}.{current_key}".strip('.')
                
                print(f"{raw_line.strip()[:35]:<35} | Found in {potential_parent:<10} | {full_path}")
                
                # Dodajemy nowego członka na stos
                stack.append({'name': current_key, 'path': full_path})
                found_parent = True
                break
        
        if not found_parent:
            print(f"{raw_line.strip()[:35]:<35} | NOT FOUND      | ???")

# TEST NA TWOICH PROBLEMATYCZNYCH PRZYKŁADACH
test_yaml = [
    "something:",
    "  #niceObject:",
    "  #  child111: 90909",      # Tu był zły indent (2 zamiast 4)
    "  #  child222: true",       # Tu też
    "abecadlo: {}",              # Rodzic z {}
    "  # abc.def.ghi/jkl: 'val'" # Klucz ze slashami i kropkami
]

simulate_backtracking_logic(test_yaml)

