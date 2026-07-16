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

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth as auth_v1
from app.api.v1 import dashboard as dashboard_v1
from app.api.v1 import scheduling as scheduling_v1
from app.api.v1 import webhook as webhook_v1
from app.api.v1.followup import router as followup_router

from app.config import get_settings

from app.events.followup_subscribers import register_subscribers as register_followup_subscribers

from app.integrations.postgres.database import create_tables, dispose_engine
from app.utils.logger import configure_logging, get_logger
from app.worker.followup_worker import worker_loop as followup_worker_loop


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

    # Start Event Subscriptions
    
    
    register_followup_subscribers()
    logger.info("Event subscribers registered")
    
    from app.domain.kpi.bootstrap import bootstrap_kpis
    bootstrap_kpis()
    logger.info("KPI calculators registered")
    
    from app.domain.health.bootstrap import bootstrap_health
    bootstrap_health()
    logger.info("Operational Health evaluators registered")
    
    from app.domain.insight.bootstrap import bootstrap_insights
    bootstrap_insights()
    logger.info("Insight generators registered")
    
    from app.domain.recommendation.bootstrap import bootstrap_recommendations
    bootstrap_recommendations()
    logger.info("Recommendation generators registered")
    
    from app.domain.briefing.bootstrap import bootstrap_briefings
    bootstrap_briefings()
    logger.info("Executive Briefing templates registered")
    
    from app.domain.integration.bootstrap import bootstrap_integrations
    bootstrap_integrations()
    logger.info("Integration Connectors registered")

    # Start background workers
    app.state.followup_worker_task = asyncio.create_task(followup_worker_loop())

    logger.info("hunteros_engage_ready", routes_registered=True)

    yield  # ── Application runs here ──────────────────────────────────────────

    logger.info("hunteros_engage_shutting_down")
    if hasattr(app.state, "followup_worker_task"):
        app.state.followup_worker_task.cancel()
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
    app.include_router(scheduling_v1.router, prefix="/api/v1")
    
    app.include_router(followup_router, prefix="/api/v1")
    app.include_router(dashboard_v1.ws_router)
    
    from app.domain.livestream.router import router as livestream_router
    from app.domain.livestream.router import ws_router as livestream_ws_router
    app.include_router(livestream_router)
    app.include_router(livestream_ws_router)
    
    from app.domain.kpi.router import router as kpi_router
    app.include_router(kpi_router, prefix="/api/v1")
    
    from app.domain.health.router import router as health_router
    app.include_router(health_router, prefix="/api/v1")
    
    from app.domain.insight.router import router as insight_router
    app.include_router(insight_router, prefix="/api/v1")
    
    from app.domain.recommendation.router import router as recommendation_router
    app.include_router(recommendation_router, prefix="/api/v1")
    
    from app.domain.briefing.router import router as briefing_router
    app.include_router(briefing_router, prefix="/api/v1")
    
    from app.domain.integration.router import router as integration_router
    app.include_router(integration_router, prefix="/api/v1")
    
    from app.domain.action.router import router as action_router
    app.include_router(action_router, prefix="/api/v1")
    
    from app.domain.approval.router import router as approval_router
    app.include_router(approval_router, prefix="/api/v1")
    
    from app.domain.operations.router import router as operations_router
    app.include_router(operations_router, prefix="/api/v1")
    
    from app.api.v1.dev import router as dev_router
    app.include_router(dev_router)

    if settings.enable_developer_tools:
        from app.developer_tools.middleware import LatencyMiddleware
        app.add_middleware(LatencyMiddleware)
        from app.developer_tools.router import router as dev_tools_router
        app.include_router(dev_tools_router)

    # ── System endpoints ──────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], summary="Health Check")
    async def health_check() -> dict:
        """Returns service health status. Used by load balancers and monitors."""
        return {
            "status": "healthy",
            "service": "HunterOS Engage",
            "version": "1.0.0",
            "phase": 1,
        }

    return app




# ── Entry point ───────────────────────────────────────────────────────────────
# uvicorn app.main:app --reload
app = create_app()
