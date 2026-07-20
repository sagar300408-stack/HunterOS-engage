import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

from app.domain.observability.engines.metrics import http_requests_total, http_request_duration_seconds

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Inject request ID into logging context
        logger = logging.getLogger("hunteros")
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.requestId = request_id
            return record
            
        logging.setLogRecordFactory(record_factory)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                http_status=response.status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        finally:
            # Restore log factory to prevent leaking memory across requests
            logging.setLogRecordFactory(old_factory)
