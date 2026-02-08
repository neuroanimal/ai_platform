import logging
import os

class TraceHandler:
    """Structured logging with decision tracking."""

    def __init__(self, component: str, log_path: str = None):
        self.logger = logging.getLogger(component)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')

        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            fh = logging.FileHandler(log_path, encoding='utf-8')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def info(self, msg: str):
        self.logger.info(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def trace_decision(self, step: str, reason: str, confidence: float = 1.0):
        self.logger.info(f"[DECISION] {step} | {confidence*100:.0f}% | {reason}")
