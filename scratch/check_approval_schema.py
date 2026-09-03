import asyncio
import os
from pathlib import Path

_env = Path(".env")
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

raw = os.environ.get("DATABASE_URL", "")
if raw.startswith("postgresql://"):
    url = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw.startswith("postgres://"):
    url = raw.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    url = raw

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def main():
    engine = create_async_engine(url, echo=False)
    async with engine.connect() as conn:
        res = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name IN "
            "('approval_policies','approval_requests','approval_decisions')"
        ))
        existing = [r[0] for r in res.fetchall()]
        print("Existing approval tables:", existing)

        for tbl in existing:
            cols = await conn.execute(text(
                f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_name='{tbl}' ORDER BY ordinal_position"
            ))
            print(f"  {tbl} columns:", [r[0] for r in cols.fetchall()])
    await engine.dispose()


asyncio.run(main())
