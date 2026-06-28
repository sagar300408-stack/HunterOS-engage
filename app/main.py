"""
HunterOS Engage — FastAPI Application Factory

Responsibilities:
  - Configure structured logging
  - Initialize the database connection pool
  - Register all versioned routers
  - Configure CORS for the React dashboard
  - Expose health check endpoint
  - Manage lifespan (startup + graceful shutdown)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth as auth_v1
from app.api.v1 import dashboard as dashboard_v1
from app.api.v1 import webhook as webhook_v1
from app.config import get_settings
from app.integrations.postgres.database import create_tables, dispose_engine
from app.utils.logger import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:  configure logging → create DB tables (dev) → seed admin user → log ready
    Shutdown: dispose DB engine → log shutdown
    """
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    logger.info(
        "hunteros_engage_starting",
        env=settings.app_env,
        log_level=settings.log_level,
        active_prompt_version=settings.active_prompt_version,
        model=settings.openai_model,
    )

    # Auto-create tables in development.
    # In staging/production, use: alembic upgrade head
    if settings.is_development:
        await create_tables()
        from app.startup.seeder import seed_default_admin
        await seed_default_admin()

    logger.info("hunteros_engage_ready", routes_registered=True)

    yield  # ── Application runs here ──────────────────────────────────────────

    logger.info("hunteros_engage_shutting_down")
    await dispose_engine()
    logger.info("hunteros_engage_stopped")


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Returns the configured app instance for use with uvicorn:
        uvicorn app.main:app --reload
    """
    settings = get_settings()

    app = FastAPI(
        title="HunterOS Engage",
        description=(
            "AI-Powered Customer Engagement Platform\n\n"
            "Phase 4: Live Dashboard — Operational mission control with RBAC, "
            "multi-tenancy, audit logging, AI explainability, event replay, "
            "queue monitoring, cost analytics, and real-time WebSocket updates.\n"
            "Built for production. Designed for every future phase."
        ),
        version="4.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS — allow React dashboard dev server ───────────────────────────────
    origins = [o.strip() for o in settings.dashboard_cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(webhook_v1.router)
    app.include_router(auth_v1.router)
    app.include_router(dashboard_v1.router)
    app.include_router(dashboard_v1.ws_router)   # WebSocket at /ws/dashboard

    # ── System endpoints ──────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], summary="Health Check")
    async def health_check() -> dict:
        """Returns service health status. Used by load balancers and monitors."""
        return {
            "status": "healthy",
            "service": "HunterOS Engage",
            "version": "4.0.0",
            "phase": 4,
        }

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
# uvicorn app.main:app --reload
app = create_app()
