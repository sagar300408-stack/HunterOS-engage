"""
Seed an admin user so you can log in to the dashboard.
Run once:  python scripts/seed_admin.py
"""
import asyncio
import sys
import os

# Make sure app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from app.integrations.postgres.database import get_session_factory, get_engine
from app.domain.security.models import User, UserRole, DEFAULT_WORKSPACE_ID
from app.domain.dashboard.service import hash_password

ADMIN_EMAIL    = "admin@hunteros.com"
ADMIN_PASSWORD = "hunter123"
ADMIN_NAME     = "HunterOS Admin"


async def seed():
    # Ensure tables exist
    from app.integrations.postgres.database import create_tables
    await create_tables()

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if existing:
            print(f"✅ Admin user already exists: {ADMIN_EMAIL}")
            return

        admin = User(
            workspace_id=DEFAULT_WORKSPACE_ID,
            email=ADMIN_EMAIL,
            full_name=ADMIN_NAME,
            role=UserRole.admin,
            password_hash=hash_password(ADMIN_PASSWORD),
            is_active="true",
        )
        session.add(admin)
        await session.commit()
        print(f"✅ Admin user created!")
        print(f"   Email:    {ADMIN_EMAIL}")
        print(f"   Password: {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
