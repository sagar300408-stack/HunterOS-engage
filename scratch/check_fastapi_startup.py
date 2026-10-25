import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())

async def test_fastapi_startup():
    from app.main import create_app
    print("[STARTUP TEST] Building FastAPI app via create_app()...")
    app = create_app()
    print("[STARTUP TEST] App created. Entering lifespan context...")
    try:
        async with app.router.lifespan_context(app):
            print("[STARTUP TEST] Entered lifespan successfully!")
            print(f"[STARTUP TEST] Routes count: {len(app.routes)}")
            print(f"[STARTUP TEST] Event bus present on app.state: {hasattr(app.state, 'event_bus')}")
            print(f"[STARTUP TEST] Consumer registry present on app.state: {hasattr(app.state, 'consumer_registry')}")
            print(f"[STARTUP TEST] Context resolver present on app.state: {hasattr(app.state, 'context_resolver')}")
        print("[STARTUP TEST] Lifespan shutdown completed cleanly.")
        return True
    except Exception as e:
        import traceback
        print(f"[STARTUP TEST] Lifespan failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fastapi_startup())
    print(f"[STARTUP TEST RESULT] Success={success}")
