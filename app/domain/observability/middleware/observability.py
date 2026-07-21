import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

from app.domain.observability.engines.metrics import http_requests_total, http_request_duration_seconds
from app.utils.context import correlation_id_context, trace_id_context

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Inject correlation_id and trace_id from headers if present, else generate
        raw_correlation_id = request.headers.get("X-Correlation-ID")
        correlation_id = None
        if raw_correlation_id:
            try:
                correlation_id = uuid.UUID(raw_correlation_id)
            except ValueError:
                correlation_id = uuid.uuid4()
        else:
            correlation_id = uuid.uuid4()
            
        trace_id = request.headers.get("X-Trace-ID", request_id)
        
        token_corr = correlation_id_context.set(correlation_id)
        token_trace = trace_id_context.set(trace_id)
        
        # Inject request ID into logging context
        logger = logging.getLogger("hunteros")
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.requestId = request_id
            record.correlationId = str(correlation_id)
            record.traceId = trace_id
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
            response.headers["X-Correlation-ID"] = str(correlation_id)
            response.headers["X-Trace-ID"] = trace_id
            return response
            
        finally:
            # Restore log factory to prevent leaking memory across requests
            logging.setLogRecordFactory(old_factory)
            correlation_id_context.reset(token_corr)
            trace_id_context.reset(token_trace)
