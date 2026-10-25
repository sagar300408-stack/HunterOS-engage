import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    print("Inside main with SelectorEventLoop")

asyncio.run(main())
print("Completed successfully!")
