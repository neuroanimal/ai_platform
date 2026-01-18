"""
Trace Handler - Unified logging and debugging system
Integrated from uncomment project with enhancements
"""
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any


class TraceHandler:
    """Enhanced trace handler for comprehensive logging and debugging"""
    
    def __init__(self, product: str, version: str, component: str, log_level: str = "INFO"):
        self.product = product
        self.version = version
        self.component = component
        
        # Setup logger
        self.logger = logging.getLogger(f"{product}.{component}")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # Decision tracking
        self.decisions = []
        self.stats = {"info": 0, "warning": 0, "error": 0, "debug": 0}
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message)
        self.stats["info"] += 1
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message)
        self.stats["warning"] += 1
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message)
        self.stats["error"] += 1
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message)
        self.stats["debug"] += 1
    
    def trace_decision(self, step: str, reason: str, metadata: Optional[Dict[str, Any]] = None):
        """Track decision points for analysis"""
        decision = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "reason": reason,
            "metadata": metadata or {}
        }
        self.decisions.append(decision)
        self.debug(f"DECISION [{step}]: {reason}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get logging summary"""
        return {
            "component": f"{self.product}.{self.component}",
            "stats": self.stats,
            "decisions_count": len(self.decisions)
        }