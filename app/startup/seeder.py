"""
Startup seeder — seeds default admin user in development.

Creates admin@hunteros.ai / admin123 if no users exist in the DB.
Safe to call on every restart — idempotent via count check.
"""

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def seed_default_admin() -> None:
    """Ensure a default admin user exists. No-op if any user already exists."""
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.security.models import DEFAULT_WORKSPACE_ID, User, UserRole
    from app.domain.dashboard.service import hash_password
    from app.integrations.postgres.database import get_engine

    engine = get_engine()
    async with AsyncSession(engine) as session:
        async with session.begin():
            existing = await session.scalar(select(func.count(User.id)))
            if existing == 0:
                admin = User(
                    email="admin@hunteros.ai",
                    full_name="HunterOS Admin",
                    password_hash=hash_password("admin123"),
                    role=UserRole.admin,
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    is_active="true",
                )
                session.add(admin)
                logger.info(
                    "default_admin_seeded",
                    email="admin@hunteros.ai",
                    warning="Change this password immediately in production!",
                )
            else:
                logger.debug("admin_seed_skipped", existing_users=existing)
