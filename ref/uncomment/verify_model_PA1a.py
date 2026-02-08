import sys
from common.trace_handler import TraceHandler
from engines.ai_engine.structure_model import StructureModel
from engines.io_engine.helm_module import HelmModule
from engines.io_engine.json_module import JSONModule

def verify():
    # Inicjalizacja podstawowych komponentów
    tracer = TraceHandler("VERIFY", "0.0", "Tool")
    model = StructureModel(tracer, None)

    # Symulacja wczytywania danych (podmien sciezki na swoje testowe)
    helm_io = HelmModule(tracer)
    json_io = JSONModule(tracer)

    print("--- Ladowanie danych do testu ---")
    # Tutaj ladujemy tylko wycinek lub calosc, by sprawdzic model
    # helm_data = helm_io.read_all_charts("data/ANONYMOUS/0.01/input/structure/helm")
    # json_params = json_io.read_parameters("data/ANONYMOUS/0.01/input/structure/flat/params.json")
    # model.build_from_sources(helm_data, {})
    # model.ingest_json_parameters(json_params)

    print("\nSystem gotowy. Wpisz sciezke (np. a.b.c) aby sprawdzic dopasowanie.")
    print("Wpisz 'exit' aby wyjsc.\n")

    while True:
        path = input("Podaj sciezke do sprawdzenia: ")
        if path.lower() == 'exit':
            break

        node = model.resolve_path_context(path)

        if node:
            print(f"? SUKCES!")
            print(f"   Typ wezla: {node.node_type}")
            print(f"   Zródlo: {node.metadata.get('source', 'unknown')}")
            print(f"   Dzieci: {list(node.children.keys())}")
        else:
            print(f"? BRAK DOPASOWANIA dla: {path}")
            # Podpowiedz: sprawdzmy czy pierwszy czlon w ogóle istnieje
            root_key = path.split('.')[0]
            if root_key in model.root.children:
                print(f"   (Podpowiedz: Klucz '{root_key}' istnieje w root, ale sciezka dalej sie urywa)")
            else:
                print(f"   (Podpowiedz: Klucz '{root_key}' nie istnieje nawet w root modelu)")

if __name__ == "__main__":
    verify()
