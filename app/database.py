"""
Convenience shim so routers can import from `app.database` directly.

The canonical implementation lives in app.integrations.postgres.database.
"""

from app.integrations.postgres.database import (  # noqa: F401
    get_db,
    get_db_session,
    get_engine,
    get_session,
    get_session_factory,
    create_tables,
    dispose_engine,
)

# Also expose the session maker used by seed scripts
from app.integrations.postgres.database import get_session_factory as _factory

def async_session_maker():
    return _factory()
