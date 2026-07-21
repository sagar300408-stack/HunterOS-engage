import contextvars
from uuid import UUID
from typing import Optional

is_demo_context = contextvars.ContextVar("is_demo", default=False)
correlation_id_context = contextvars.ContextVar[Optional[UUID]]("correlation_id", default=None)
trace_id_context = contextvars.ContextVar[Optional[str]]("trace_id", default=None)
