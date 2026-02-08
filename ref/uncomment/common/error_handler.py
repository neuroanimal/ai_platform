from .trace_handler import TraceHandler

class BaseEngineError(Exception):
    """Bazowy blad dla wszystkich silników."""
    def __init__(self, message: str, recoverable: bool = False):
        super().__init__(message)
        self.recoverable = recoverable

class PathNotFoundError(BaseEngineError):
    """Blad gdy sciezka w modelu struktury nie istnieje."""
    pass

class ValidationError(BaseEngineError):
    """Blad walidacji (np. Linter). Zazwyczaj naprawialny przez AI."""
    def __init__(self, message: str, line_no: int = None):
        super().__init__(message, recoverable=True)
        self.line_no = line_no

class ErrorHandler:
    """Centralny punkt zarzadzania bledami w systemie."""

    @staticmethod
    def handle(error: Exception, tracer: TraceHandler):
        if isinstance(error, BaseEngineError):
            status = "RECOVERABLE" if error.recoverable else "FATAL"
            tracer.logger.error(f"[{status} ERROR] {str(error)}")
            if not error.recoverable:
                raise error
        else:
            tracer.logger.critical(f"[UNEXPECTED SYSTEM ERROR] {str(error)}")
            raise error