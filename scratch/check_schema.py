import asyncio
import sqlalchemy as sa
from app.integrations.postgres.database import get_engine

async def run():
    engine = get_engine()
    async with engine.connect() as conn:
        res = await conn.execute(sa.text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'"))
        print(res.fetchall())
        
if __name__ == "__main__":
    asyncio.run(run())
