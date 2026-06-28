from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SimulationStateSchema(BaseModel):
    openai_status: str = Field(..., description="online | timeout | offline")
    database_status: str = Field(..., description="online | slow | offline")
    whatsapp_status: str = Field(..., description="online | offline")
    redis_status: str = Field(..., description="online | offline")
    email_status: str = Field(..., description="online | offline")
    worker_status: str = Field(..., description="online | offline")
    queue_status: str = Field(..., description="online | overflow | offline")
    latency_ms: int = Field(..., description="artificial API response latency in milliseconds")
    mock_ai: bool = Field(..., description="whether to mock OpenAI calls")
    mock_whatsapp: bool = Field(..., description="whether to mock WhatsApp Cloud API calls")
    time_offset_seconds: int = Field(..., description="simulated clock offset in seconds")

class ToggleSimulationSchema(BaseModel):
    openai_status: Optional[str] = None
    database_status: Optional[str] = None
    whatsapp_status: Optional[str] = None
    redis_status: Optional[str] = None
    email_status: Optional[str] = None
    worker_status: Optional[str] = None
    queue_status: Optional[str] = None
    latency_ms: Optional[int] = None
    mock_ai: Optional[bool] = None
    mock_whatsapp: Optional[bool] = None

class TriggerScenarioSchema(BaseModel):
    scenario_name: str = Field(..., description="name of the JSON template under app/developer_tools/scenarios/")

class WebhookSimulateSchema(BaseModel):
    channel: str = Field(..., description="Website | WhatsApp | Email | Instagram | Messenger | REST API")
    contact_name: str = Field(..., description="Name of the customer profile")
    identifier: str = Field(..., description="Unique phone number or string identifier")
    message: str = Field(..., description="Text message content")

class GenerateJobsSchema(BaseModel):
    job_type: str = Field(..., description="crm_sync | followup_schedule | memory_update | email")
    count: int = Field(default=10, ge=1)

class TimeTravelSchema(BaseModel):
    seconds: int = Field(..., description="Seconds to travel forward in time")

class ResetSchema(BaseModel):
    clear_conversations: bool = False
    clear_buyers: bool = False
    clear_activity: bool = False
    clear_queue: bool = False
    clear_audit_logs: bool = False
    reset_everything: bool = False

class PerformanceMetricsSchema(BaseModel):
    cpu_usage_pct: float
    ram_usage_pct: float
    db_latency_ms: int
    avg_api_latency_ms: float
    total_token_usage: int
    avg_token_usage_per_response: float
    websocket_throughput: int

class TimelineEventSchema(BaseModel):
    timestamp: datetime
    type: str
    channel: Optional[str] = None
    identifier: Optional[str] = None
    event: str
    metadata: Optional[Dict[str, Any]] = None

class ReplayTimelineSchema(BaseModel):
    scenario_name: str
    timeline: List[Dict[str, Any]]

class TestCaseResult(BaseModel):
    name: str
    passed: bool
    details: Optional[str] = None

class CategoryResult(BaseModel):
    category: str
    passed: int
    failed: int
    test_cases: List[TestCaseResult]

class RegressionSuiteSchema(BaseModel):
    timestamp: datetime
    success: bool
    summary: Dict[str, Any]
    results: List[CategoryResult]
