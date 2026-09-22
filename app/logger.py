import json
import logging
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "custom_data"):
            log_entry.update(record.custom_data)
        
        # Format exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

def setup_logger():
    logger = logging.getLogger("hr_assistant")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.FileHandler("app.log")
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    return logger

logger = setup_logger()

def log_event(message: str, level: int = logging.INFO, **kwargs):
    """
    Logs an event with structured data.
    Usage: log_event("LLM Request", employee_id="E001", tokens=150)
    """
    logger.log(level, message, extra={"custom_data": kwargs})
