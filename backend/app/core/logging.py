"""
Structured JSON logging configuration with request IDs.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        
        # Add extra fields from the record
        extra_fields = [
            "request_id", "path", "method", "status_code", 
            "user_id", "duration_ms", "traceback"
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to use JSON formatting (True for production)
    """
    # Remove any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_logs:
        # Use JSON formatter for production
        formatter = JSONFormatter()
    else:
        # Use simple formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s',
            defaults={'request_id': 'N/A'}
        )
    
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Set specific levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


class RequestLogger:
    """Context manager for adding request ID to all log messages within a request."""
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            if not hasattr(record, 'request_id'):
                record.request_id = self.request_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)