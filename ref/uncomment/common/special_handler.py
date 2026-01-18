class SpecialHandler:
    """
    Zarzadza transformacjami nazw specjalnych miedzy JSON a YAML.
    Np. (aaa.bbb) w JSON moze oznaczac klucz "aaa.bbb" w YAML.
    """
    @staticmethod
    def normalize_for_yaml(token: str) -> str:
        # Usuwamy nawiasy i cudzyslowy, jesli YAML ich nie wymaga
        return token.replace('(', '').replace(')', '').replace('"', '').replace("'", "")

    @staticmethod
    def is_complex(token: str) -> bool:
        return any(c in token for c in "()/\\")

