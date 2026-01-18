class BaseEngineError(Exception):
    """Base error for all engines."""
    def __init__(self, message: str, recoverable: bool = False):
        super().__init__(message)
        self.recoverable = recoverable

class ValidationError(BaseEngineError):
    """Validation error (usually recoverable)."""
    def __init__(self, message: str, line_no: int = None):
        super().__init__(message, recoverable=True)
        self.line_no = line_no

class ErrorHandler:
    """Centralized error management."""
    
    @staticmethod
    def handle(error: Exception, tracer):
        if isinstance(error, BaseEngineError):
            status = "RECOVERABLE" if error.recoverable else "FATAL"
            tracer.error(f"[{status}] {str(error)}")
            if not error.recoverable:
                raise error
        else:
            tracer.error(f"[UNEXPECTED] {str(error)}")
            raise error
