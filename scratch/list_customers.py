import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())

from app.integrations.postgres.database import get_session
from app.domain.customers.models import Customer
from sqlalchemy import select

async def main():
    async with get_session() as s:
        res = await s.execute(select(Customer.phone, Customer.name, Customer.id))
        rows = res.all()
        print(f"Total customers in DB: {len(rows)}")
        for row in rows:
            print(f"Customer in DB: phone={row[0]} name={row[1]} id={row[2]}")

if __name__ == "__main__":
    asyncio.run(main())
