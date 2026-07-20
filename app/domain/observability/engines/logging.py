import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime

class HunterOSJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        if not log_record.get('timestamp'):
            # This follows ISO8601
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            
        if log_record.get('level'):
            log_record['severity'] = log_record['level'].upper()
        else:
            log_record['severity'] = record.levelname
            
        # Defaults if not injected by ContextVars (handled in middleware)
        log_record.setdefault("requestId", "unknown")
        log_record.setdefault("organizationId", "unknown")

def configure_structured_logging():
    """
    Replaces standard logging with JSON structured logging.
    """
    logger = logging.getLogger()
    
    # Remove existing handlers
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])
        
    logHandler = logging.StreamHandler()
    formatter = HunterOSJsonFormatter('%(timestamp)s %(severity)s %(name)s %(message)s')
    logHandler.setFormatter(formatter)
    
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    
    # Silence noisy libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Expose a configured logger instance
logger = logging.getLogger("hunteros")
