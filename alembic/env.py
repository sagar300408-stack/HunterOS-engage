"""
Alembic environment configuration for HunterOS Engage.

Reads DATABASE_URL from the environment at runtime so no credentials
are ever stored in alembic.ini.

Usage:
    # Apply all pending migrations
    alembic upgrade head

    # Generate a new migration after model changes
    alembic revision --autogenerate -m "describe_your_change"

    # Downgrade one step
    alembic downgrade -1
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

# Load ORM models so Alembic can detect changes
from app.domain.conversations.models import Base  # noqa: F401
from app.domain.customers.models import Customer  # noqa: F401
from app.domain.memory.models import (  # noqa: F401
    CustomerMemory,
    CustomerMemoryVersion,
    CustomerMemoryEvent,
)
from app.domain.intent.models import IntentHistory  # noqa: F401
from app.domain.dashboard.models import (  # noqa: F401
    User,
    AuditLog,
    PipelineEvent,
    BackgroundJob,
)
from app.domain.scheduling.models import (  # noqa: F401
    ScheduledEvent,
    SchedulingCandidate,
    EventAuditLog,
    CustomerAvailabilityPreferences,
)
from app.domain.followup.models import (  # noqa: F401
    FollowUpQueue,
    FollowUpExecution,
    LeadHealthScore,
    SalesMemoryTimeline,
)
from app.events.store.models import EventRecord  # noqa: F401

# Alembic Config object (gives access to alembic.ini values)
config = context.config

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the metadata for autogenerate support
target_metadata = Base.metadata

# Load DATABASE_URL from environment (overrides alembic.ini placeholder)
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Copy .env.example to .env and configure your database URL."
    )

config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL scripts without a live database connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using an async engine.
    """
    connectable = create_async_engine(DATABASE_URL, echo=False)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
