import contextvars

is_demo_context = contextvars.ContextVar("is_demo", default=False)
