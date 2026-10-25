import asyncio
from sqlalchemy import text
from app.integrations.postgres.database import get_session

async def check():
    async with get_session() as s:
        ver = (await s.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        print(f"ALEMBIC_VERSION: {ver}")
        
        cols = (await s.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'timeline_entries' AND column_name = 'action_id'
        """))).fetchall()
        print(f"COLUMN_INFO: {cols}")
        
        idx = (await s.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'timeline_entries' AND indexname = 'ix_timeline_entries_action_id'
        """))).fetchall()
        print(f"INDEX_INFO: {idx}")

if __name__ == "__main__":
    asyncio.run(check())
