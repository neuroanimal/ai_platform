"""
Error Handler - Unified error management system
Integrated from uncomment project with enhancements
"""
from typing import Optional, Dict, Any
from common.handler.trace_handler import TraceHandler


class BaseEngineError(Exception):
    """Base exception for all engine errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.metadata = metadata or {}


class FormatProcessingError(BaseEngineError):
    """Error in format processing operations"""
    pass


class AIEngineError(BaseEngineError):
    """Error in AI engine operations"""
    pass


class ValidationError(BaseEngineError):
    """Error in validation operations"""
    pass


class ErrorHandler:
    """Centralized error handling and recovery"""

    @staticmethod
    def handle(error: Exception, tracer: TraceHandler, context: Optional[str] = None) -> bool:
        """
        Handle errors with logging and potential recovery
        Returns True if error was handled and processing can continue
        """
        error_context = f" in {context}" if context else ""

        if isinstance(error, BaseEngineError):
            tracer.error(f"Engine Error{error_context}: {str(error)}")
            if error.metadata:
                tracer.debug(f"Error metadata: {error.metadata}")
            return False

        elif isinstance(error, (FileNotFoundError, PermissionError)):
            tracer.error(f"File System Error{error_context}: {str(error)}")
            return False

        elif isinstance(error, (ValueError, TypeError)):
            tracer.error(f"Data Error{error_context}: {str(error)}")
            return False

        else:
            tracer.error(f"Unexpected Error{error_context}: {str(error)}")
            return False

    @staticmethod
    def create_error(error_type: str, message: str, **kwargs) -> BaseEngineError:
        """Factory method for creating typed errors"""
        error_classes = {
            "format": FormatProcessingError,
            "ai": AIEngineError,
            "validation": ValidationError
        }

        error_class = error_classes.get(error_type, BaseEngineError)
        return error_class(message, **kwargs)