import asyncio
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        """Introduce artificial request lag if latency_ms is configured in SimulationState."""
        # Only slow down API routes under /api/v1/ (excluding developer-tools routes themselves to keep console responsive)
        if request.url.path.startswith("/api/v1") and not request.url.path.startswith("/api/v1/developer-tools"):
            try:
                from app.developer_tools.service import simulation_state
                if simulation_state.latency_ms > 0:
                    await asyncio.sleep(simulation_state.latency_ms / 1000.0)
            except ImportError:
                pass
                
        response = await call_next(request)
        return response
