from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.config import get_settings
from app.api.v1.auth_deps import get_current_user
from app.integrations.postgres.database import get_db
from app.domain.security.models import User, UserRole
from app.domain.dashboard.service import create_background_job
from app.developer_tools.schemas import (
    SimulationStateSchema,
    ToggleSimulationSchema,
    TriggerScenarioSchema,
    WebhookSimulateSchema,
    GenerateJobsSchema,
    TimeTravelSchema,
    ResetSchema,
    PerformanceMetricsSchema,
    TimelineEventSchema,
    RegressionSuiteSchema,
    ReplayTimelineSchema,
)
from app.developer_tools.service import (
    simulation_state,
    SIMULATION_WORKSPACE_ID,
    ensure_scenario_templates,
    trigger_scenario_run,
    build_simulated_payload,
    dispatch_webhook_payload,
    time_travel,
    reset_demo_data,
    run_regression_suite,
    get_performance_metrics,
)

# Guard: Ensure Developer Tools are enabled in configuration
def require_dev_tools_enabled():
    if not get_settings().enable_developer_tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Developer Tools API is not active in this environment."
        )

# Guard: Ensure the user is authenticated as a Founder
async def require_founder(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.founder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. Developer Tools are restricted to the Founder role."
        )
    return user

router = APIRouter(
    prefix="/api/v1/developer-tools",
    tags=["Developer Tools"],
    dependencies=[Depends(require_dev_tools_enabled), Depends(require_founder)]
)

@router.get("/config", response_model=SimulationStateSchema, summary="Get Current Simulation Configuration")
async def get_config() -> dict:
    return {
        "openai_status": simulation_state.openai_status,
        "database_status": simulation_state.database_status,
        "whatsapp_status": simulation_state.whatsapp_status,
        "redis_status": simulation_state.redis_status,
        "email_status": simulation_state.email_status,
        "worker_status": simulation_state.worker_status,
        "queue_status": simulation_state.queue_status,
        "latency_ms": simulation_state.latency_ms,
        "mock_ai": simulation_state.mock_ai,
        "mock_whatsapp": simulation_state.mock_whatsapp,
        "time_offset_seconds": simulation_state.time_offset_seconds,
    }

@router.post("/simulation", response_model=SimulationStateSchema, summary="Update Simulation Configuration")
async def update_config(body: ToggleSimulationSchema) -> dict:
    if body.openai_status is not None:
        simulation_state.openai_status = body.openai_status
    if body.database_status is not None:
        simulation_state.database_status = body.database_status
    if body.whatsapp_status is not None:
        simulation_state.whatsapp_status = body.whatsapp_status
    if body.redis_status is not None:
        simulation_state.redis_status = body.redis_status
    if body.email_status is not None:
        simulation_state.email_status = body.email_status
    if body.worker_status is not None:
        simulation_state.worker_status = body.worker_status
    if body.queue_status is not None:
        simulation_state.queue_status = body.queue_status
    if body.latency_ms is not None:
        simulation_state.latency_ms = body.latency_ms
    if body.mock_ai is not None:
        simulation_state.mock_ai = body.mock_ai
    if body.mock_whatsapp is not None:
        simulation_state.mock_whatsapp = body.mock_whatsapp
        
    return await get_config()

@router.post("/trigger-scenario", summary="Trigger Customer Journey Scenario")
async def trigger_scenario(body: TriggerScenarioSchema, session: AsyncSession = Depends(get_db)) -> dict:
    ensure_scenario_templates()
    results = await trigger_scenario_run(session, body.scenario_name)
    return {"status": "success", "scenario": body.scenario_name, "steps_executed": len(results), "timeline": results}

@router.post("/webhook-simulate", summary="Simulate Multi-channel Webhook Event")
async def webhook_simulate(body: WebhookSimulateSchema, session: AsyncSession = Depends(get_db)) -> dict:
    payload = build_simulated_payload(
        channel=body.channel,
        contact_name=body.contact_name,
        identifier=body.identifier,
        message=body.message
    )
    payload["workspace_id"] = str(SIMULATION_WORKSPACE_ID)
    
    result = await dispatch_webhook_payload(session, payload)
    
    # Log to timeline
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "webhook_simulator",
        "channel": body.channel,
        "identifier": body.identifier,
        "event": "incoming_webhook_received",
        "details": f"Dispatched payload for {body.contact_name} on {body.channel}"
    }
    simulation_state.active_timeline.append(event)
    
    return {"status": "success", "webhook_result": result, "dispatched_payload": payload}

@router.post("/generate-jobs", summary="Generate Queue Background Work")
async def generate_jobs(body: GenerateJobsSchema, session: AsyncSession = Depends(get_db)) -> dict:
    jobs = []
    # Temporarily set demo context so created background jobs are marked is_demo = True
    from app.utils.context import is_demo_context
    is_demo_context.set(True)
    
    for i in range(body.count):
        job = await create_background_job(
            session=session,
            job_type=body.job_type,
            workspace_id=SIMULATION_WORKSPACE_ID
        )
        jobs.append(str(job.id))
        
    await session.commit()
    
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "queue_generator",
        "event": f"generated_{body.count}_jobs",
        "details": f"Populated {body.count} pending {body.job_type} background tasks."
    }
    simulation_state.active_timeline.append(event)
    
    return {"status": "success", "job_type": body.job_type, "count": body.count, "created_job_ids": jobs}

@router.post("/time-travel", summary="Advance Time Machine")
async def post_time_travel(body: TimeTravelSchema, session: AsyncSession = Depends(get_db)) -> dict:
    res = await time_travel(session, body.seconds)
    return {"status": "success", "time_travel_results": res}

@router.get("/timeline", response_model=List[Dict[str, Any]], summary="Get Timeline Trace Logs")
async def get_timeline() -> List[dict]:
    return simulation_state.active_timeline

@router.post("/timeline/clear", summary="Clear Timeline Trace Logs")
async def clear_timeline() -> dict:
    simulation_state.active_timeline = []
    return {"status": "success", "message": "Timeline logs cleared."}

@router.post("/timeline/replay", summary="Replay Recorded Timeline JSON")
async def replay_timeline(body: ReplayTimelineSchema, session: AsyncSession = Depends(get_db)) -> dict:
    events = body.timeline
    replayed = 0
    import asyncio
    for ev in events:
        # Support both direct webhook simulator and step events in the timeline
        if ev.get("type") in ["webhook_simulator", "scenario_step"] or (ev.get("type") == "timeline_event" and "message" in ev):
            payload = build_simulated_payload(
                channel=ev.get("channel") or "WhatsApp",
                contact_name=ev.get("name") or ev.get("contact_name") or "Replayed Customer",
                identifier=ev.get("identifier") or ev.get("phone") or "12025550143",
                message=ev.get("message") or ev.get("details", "")
            )
            payload["workspace_id"] = str(SIMULATION_WORKSPACE_ID)
            await dispatch_webhook_payload(session, payload)
            replayed += 1
            await asyncio.sleep(0.1)
            
    return {"status": "success", "scenario_name": body.scenario_name, "replayed_steps": replayed}

@router.post("/reset", summary="Safe Reset of Generated Simulation Data")
async def reset_data(body: ResetSchema, session: AsyncSession = Depends(get_db)) -> dict:
    results = await reset_demo_data(session, body)
    
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "database_reset",
        "event": "data_reset_executed",
        "details": f"Demo data cleanup completed: {results}"
    }
    simulation_state.active_timeline.append(event)
    
    return {"status": "success", "cleanup_results": results}

@router.get("/metrics", response_model=PerformanceMetricsSchema, summary="Get Performance and System Health Diagnostics")
async def get_metrics(session: AsyncSession = Depends(get_db)) -> dict:
    return await get_performance_metrics(session)

@router.post("/run-tests", response_model=RegressionSuiteSchema, summary="Run Automated Regression Suite")
async def run_tests(session: AsyncSession = Depends(get_db)) -> dict:
    results = await run_regression_suite(session)
    return results
