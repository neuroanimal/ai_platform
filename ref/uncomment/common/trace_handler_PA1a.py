import logging
import os
from datetime import datetime

class TraceHandler:
    """
    Zarzadza logowaniem procesów i zbieraniem statystyk.
    Obsluguje wielopoziomowe sledzenie decyzji AI.
    """
    def __init__(self, product: str, version: str, component: str):
        self.log_path = f"data/{product}/{version}/output/template/process.log"
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        self.logger = logging.getLogger(f"{product}_{version}_{component}")
        self.logger.setLevel(logging.DEBUG)
        
        # Formatowanie: Czas | Poziom | Komponent | Wiadomosc
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
        
        # Handler do pliku
        fh = logging.FileHandler(self.log_path)
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # Handler do konsoli
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def info(self, msg: str):
        self.logger.info(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def trace_decision(self, step: str, reason: str, confidence: float = 1.0):
        """Specjalna metoda do logowania decyzji podejmowanych przez AI Engine."""
        self.logger.info(f"[DECISION] Step: {step} | Confidence: {confidence*100}% | Reason: {reason}")

    def save_summary(self, stats: dict, product: str, version: str, module_name: str):
        """Zapisuje statystyki do pliku statistics_summary_file."""
        summary_path = f"data/{product}/{version}/output/{module_name}/statistics_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Summary for {module_name} - {datetime.now()}\n")
            f.write("="*40 + "\n")
            for k, v in stats.items():
                f.write(f"{k}: {v}\n")