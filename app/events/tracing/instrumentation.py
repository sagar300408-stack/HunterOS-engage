"""
HunterOS Engage — Passive Tracing Instrumentation & Decorators
app/events/tracing/instrumentation.py
"""

from functools import wraps
import inspect
from typing import Any, Callable, Dict, Optional, TypeVar

from app.events.tracing.context import TraceContext
from app.events.tracing.span import Span

F = TypeVar("F", bound=Callable[..., Any])


def inject_trace_context(
    carrier_or_context: Any,
    context_or_carrier: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Injects TraceContext key-values into a carrier dictionary (e.g. metadata_payload or Celery headers).
    Flexible signature supports inject_trace_context(carrier, context) or inject_trace_context(context, carrier).
    """
    from app.events.tracing import trace_manager

    if isinstance(carrier_or_context, dict):
        carrier = carrier_or_context
        ctx = context_or_carrier or trace_manager.get_current_context()
    elif isinstance(carrier_or_context, TraceContext):
        ctx = carrier_or_context
        carrier = context_or_carrier if isinstance(context_or_carrier, dict) else {}
    else:
        carrier = {}
        ctx = trace_manager.get_current_context()

    if ctx:
        carrier.update(ctx.to_carrier_dict())
    return carrier


def extract_trace_context(carrier: Optional[Dict[str, Any]]) -> TraceContext:
    """
    Extracts TraceContext from an incoming carrier dictionary.
    """
    if not carrier:
        return TraceContext()
    return TraceContext.from_carrier_dict(carrier)


def trace_span_sync(
    component: str,
    operation: str,
    metadata_factory: Optional[Callable[..., Dict[str, Any]]] = None,
    manager: Optional[Any] = None,
) -> Callable[[F], F]:
    """
    Decorator for synchronously tracing function execution.
    Completely passive: catches no business exceptions (lets them propagate),
    and ensures tracing logic never crashes the target function.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.events.tracing import trace_manager
            mgr = manager or trace_manager

            meta = None
            if metadata_factory:
                try:
                    meta = metadata_factory(*args, **kwargs)
                except Exception:
                    pass

            with mgr.span(component=component, operation=operation, metadata=meta):
                return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def trace_span_async(
    component: str,
    operation: str,
    metadata_factory: Optional[Callable[..., Dict[str, Any]]] = None,
    manager: Optional[Any] = None,
) -> Callable[[F], F]:
    """
    Decorator for asynchronously tracing coroutine function execution.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.events.tracing import trace_manager
            mgr = manager or trace_manager

            meta = None
            if metadata_factory:
                try:
                    meta = metadata_factory(*args, **kwargs)
                except Exception:
                    pass

            async with mgr.span_async(component=component, operation=operation, metadata=meta):
                return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
