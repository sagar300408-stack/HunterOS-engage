import asyncio
import logging
import signal
import sys

from app.integrations.postgres.database import get_session_factory
from app.celery_app import celery_app
from app.events.dispatcher.poller import OutboxPoller
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    settings = get_settings()
    
    poller = OutboxPoller(
        session_factory=get_session_factory(),
        celery_app=celery_app
    )
    
    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    
    def handle_sigterm():
        logger.info("Received termination signal. Shutting down gracefully...")
        asyncio.create_task(poller.stop())

    if sys.platform != 'win32':
        loop.add_signal_handler(signal.SIGINT, handle_sigterm)
        loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
    else:
        # Windows doesn't support add_signal_handler for SIGINT/SIGTERM gracefully in asyncio
        # We rely on KeyboardInterrupt caught below
        pass

    try:
        await poller.run()
    except asyncio.CancelledError:
        logger.info("Poller task cancelled.")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
        await poller.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"Dispatcher crashed: {e}", exc_info=True)
        sys.exit(1)
