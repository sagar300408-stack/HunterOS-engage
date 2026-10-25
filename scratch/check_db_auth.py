import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())

async def check_db():
    from app.config import get_settings
    settings = get_settings()
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    print(f"[DB CHECK] Configured DB URL present: {bool(settings.database_url)}")
    try:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            row = res.scalar()
            print(f"[DB CHECK] PostgreSQL query 'SELECT 1' succeeded: {row == 1}")
        await engine.dispose()
        return True
    except Exception as e:
        print(f"[DB CHECK] PostgreSQL query failed: {type(e).__name__}: {str(e)[:100]}")
        return False

async def check_redis():
    from app.config import get_settings
    settings = get_settings()
    import redis.asyncio as aioredis
    
    broker_url = settings.celery_broker_url
    print(f"[REDIS CHECK] Configured Celery Broker URL present: {bool(broker_url)}")
    try:
        client = aioredis.from_url(broker_url)
        pong = await client.ping()
        print(f"[REDIS CHECK] Redis PING succeeded: {pong}")
        await client.aclose()
        return True
    except Exception as e:
        print(f"[REDIS CHECK] Redis PING failed: {type(e).__name__}: {str(e)[:100]}")
        return False

async def main():
    db_ok = await check_db()
    redis_ok = await check_redis()
    print(f"[INFRA SUMMARY] DB={db_ok}, Redis={redis_ok}")

if __name__ == "__main__":
    asyncio.run(main())
