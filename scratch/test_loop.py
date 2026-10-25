import asyncio
print("1: creating loop")
loop = asyncio.new_event_loop()
print("2: loop created")
async def do():
    print("3: inside do")
loop.run_until_complete(do())
print("4: done")
loop.close()
print("5: closed")
