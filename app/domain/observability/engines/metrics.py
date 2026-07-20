from prometheus_client import Counter, Histogram, Gauge
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from typing import Dict, Any

from app.domain.observability.models import MetricRecord

logger = logging.getLogger("hunteros.metrics")

# Prometheus Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "http_status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

ai_prompts_total = Counter(
    "ai_prompts_total",
    "Total number of AI prompts generated",
    ["model", "feature"]
)

business_friction_gauge = Gauge(
    "business_friction_score",
    "Current Business Friction Score for an organization",
    ["workspace_id"]
)


class MetricsEngine:
    """
    Handles persisting metrics to Prometheus and backing them up to Postgres (MetricRecord).
    """
    @staticmethod
    async def record_business_metric(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        metric_name: str,
        value: float,
        dimensions: Dict[str, Any] = None
    ):
        """
        Records a business metric (e.g. friction trend, revenue at risk) to Postgres.
        """
        record = MetricRecord(
            workspace_id=workspace_id,
            metric_name=metric_name,
            metric_value=value,
            dimensions=dimensions or {}
        )
        db.add(record)
        
        # Also update Prometheus if applicable
        if metric_name == "business_friction":
            business_friction_gauge.labels(workspace_id=str(workspace_id)).set(value)
            
        logger.info(f"Recorded business metric {metric_name}={value}", extra={
            "workspace_id": str(workspace_id),
            "metric_name": metric_name,
            "metric_value": value
        })
