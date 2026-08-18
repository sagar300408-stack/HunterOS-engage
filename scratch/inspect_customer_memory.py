import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from pathlib import Path

async def main():
    _env = Path(".env")
    if _env.exists():
        for _line in _env.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
                
    url = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(url)
    
    async with engine.begin() as conn:
        res = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'customer_memory'
        """))
        for row in res:
            print(row[0], row[1])
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
