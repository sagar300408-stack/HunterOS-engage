import os
import json
import time
import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from pathlib import Path

from sqlalchemy import select, delete, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.utils.context import is_demo_context
from app.utils.clock import SystemClock
from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation, Message, AIMetadata
from app.domain.dashboard.models import BackgroundJob, JobStatus
from app.domain.security.models import AuditLog, UserRole
from app.domain.dashboard.service import write_audit_log, create_background_job
from app.api.v1.webhook import receive_webhook
from app.developer_tools.schemas import ResetSchema

# Simulation Sandbox Workspace ID
SIMULATION_WORKSPACE_ID = UUID("00000000-0000-0000-0000-999999999999")

class SimulationState:
    def __init__(self):
        self.openai_status = "online"       # online | timeout | offline
        self.database_status = "online"     # online | slow | offline
        self.whatsapp_status = "online"     # online | offline
        self.redis_status = "online"        # online | offline
        self.email_status = "online"        # online | offline
        self.worker_status = "online"       # online | offline
        self.queue_status = "online"        # online | overflow | offline
        self.latency_ms = 0
        self.mock_ai = True
        self.mock_whatsapp = True
        self.time_offset_seconds = 0
        self.active_timeline = []
        self.next_mock_reply = None

# Global simulation state singleton
simulation_state = SimulationState()

class MockRequest:
    def __init__(self, json_data):
        self._json_data = json_data
    async def json(self):
        return self._json_data

def build_simulated_payload(channel: str, contact_name: str, identifier: str, message: str) -> dict:
    """Construct a standard Meta WhatsApp Webhook payload tagged as demo."""
    # Prefix contact name to reflect source channel visually on the dashboard
    tagged_name = f"[{channel}] {contact_name}" if channel != "WhatsApp" else contact_name
    return {
        "object": "whatsapp_business_account",
        "is_demo": True,
        "entry": [
            {
                "id": "wa_biz_id",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "16505553333",
                                "phone_number_id": "1234567890"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": tagged_name},
                                    "wa_id": identifier
                                }
                            ],
                            "messages": [
                                {
                                    "from": identifier,
                                    "id": f"wamid.simulated.{channel.lower()}.{uuid.uuid4().hex[:10]}",
                                    "timestamp": str(int(time.time())),
                                    "text": {"body": message},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

async def dispatch_webhook_payload(session: AsyncSession, payload: dict) -> dict:
    """Run a simulated payload through the production webhook endpoint."""
    is_demo_context.set(True)
    # The webhook route automatically saves rows scoped to is_demo_context.get()
    result = await receive_webhook(MockRequest(payload), session)
    return result

async def run_scenario_step(session: AsyncSession, scenario_name: str, step: dict) -> dict:
    """Execute a single scenario step and log it to the event timeline."""
    sender = step.get("sender", "customer")
    message = step.get("message", "")
    phone = step.get("phone", "12025550143")
    name = step.get("name", "Demo Buyer")
    
    event_log = {
        "timestamp": SystemClock.now().isoformat(),
        "type": "scenario_step",
        "scenario": scenario_name,
        "sender": sender,
        "phone": phone,
        "name": name,
        "message": message,
        "status": "success",
        "details": ""
    }
    
    try:
        if sender == "customer":
            # If the scenario defines a specific mock AI reply for the next turn, store it
            if "mock_reply" in step:
                simulation_state.next_mock_reply = step["mock_reply"]
                
            payload = build_simulated_payload(
                channel="WhatsApp",
                contact_name=name,
                identifier=phone,
                message=message
            )
            # Run in sandbox workspace
            payload["workspace_id"] = str(SIMULATION_WORKSPACE_ID)
            
            await dispatch_webhook_payload(session, payload)
            event_log["details"] = "Inquiry dispatched to webhook layer"
        else:
            event_log["status"] = "skipped"
            event_log["details"] = "Agent response is simulated inside the AI pipeline"
    except Exception as e:
        event_log["status"] = "failed"
        event_log["details"] = str(e)
        
    simulation_state.active_timeline.append(event_log)
    return event_log

def get_scenarios_dir() -> Path:
    return Path(__file__).parent / "scenarios"

def ensure_scenario_templates():
    """Ensure the standard scenario templates exist on disk."""
    scenarios_dir = get_scenarios_dir()
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Apartment Buyer
    apartment_json = {
        "name": "First-Time Apartment Buyer",
        "description": "Sarah Jenkins starts a search for a 1-2 bedroom apartment in Downtown under $350k.",
        "steps": [
            {
                "sender": "customer",
                "name": "Sarah Jenkins",
                "phone": "12025550143",
                "message": "Hi, I am looking to buy my first apartment in Downtown. My budget is around $350,000. I need a 1 or 2 bedroom.",
                "mock_reply": "Hello Sarah! I can help you find your first apartment. We have a couple of great 2-bedroom units in Downtown starting at $320,000. Would you like to schedule a site visit?",
                "assertions": {
                  "buying_stage": "Research",
                  "intent": "inquiry",
                  "location": "Downtown"
                }
            }
        ]
    }
    
    # 2. Villa Buyer
    villa_json = {
        "name": "Villa Buyer",
        "description": "Michael Chang inquires about a luxury 4-bedroom villa in Palm Jumeirah for $3.5M.",
        "steps": [
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "Hello, I am interested in buying a 4-bedroom villa in Palm Jumeirah. Budget is $3.5 Million.",
                "mock_reply": "Hello Michael! Palm Jumeirah has gorgeous premium villas matching your parameters. I will compile a list of available 4-bedroom luxury listings now.",
                "assertions": {
                  "buying_stage": "Research",
                  "intent": "inquiry",
                  "location": "Palm Jumeirah"
                }
            }
        ]
    }
    
    # 3. Commercial Property Buyer
    commercial_json = {
        "name": "Commercial Property Buyer",
        "description": "Apex Holdings looks for 5,000 sq ft office space in Business Bay.",
        "steps": [
            {
                "sender": "customer",
                "name": "Apex Holdings",
                "phone": "14155550211",
                "message": "We are looking for commercial office space in Business Bay. Minimum 5,000 sq ft, budget $1.2M.",
                "mock_reply": "Greetings! Business Bay has excellent commercial properties. We have three prime corporate offices fitting your layout specifications.",
                "assertions": {
                  "buying_stage": "Research",
                  "intent": "inquiry",
                  "location": "Business Bay"
                }
            }
        ]
    }

    # 4. Budget Increase
    budget_json = {
        "name": "Budget Increase",
        "description": "Sarah Jenkins increases her budget to $450k to broaden search options.",
        "steps": [
            {
                "sender": "customer",
                "name": "Sarah Jenkins",
                "phone": "12025550143",
                "message": "Hi, I'm looking to buy my first apartment in Downtown. My budget is around $350,000. I need a 1 or 2 bedroom."
            },
            {
                "sender": "customer",
                "name": "Sarah Jenkins",
                "phone": "12025550143",
                "message": "Hi, I want to increase my budget to $450,000 to see if we can get a better 2-bedroom apartment in Downtown.",
                "mock_reply": "I have updated your profile budget to $450,000. This expands our properties search to include some premium options. Let me send them over.",
                "assertions": {
                  "buying_stage": "Comparing Options",
                  "intent": "budget_update",
                  "budget": "$450,000"
                }
            }
        ]
    }

    # 5. Site Visit Request
    visit_json = {
        "name": "Site Visit Request",
        "description": "Michael Chang requests a viewing session this Saturday.",
        "steps": [
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "Hello, I am interested in buying a 4-bedroom villa in Palm Jumeirah. Budget is $3.5 Million."
            },
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "I would like to schedule a site visit to see the villa this Saturday afternoon.",
                "mock_reply": "Excellent! I have scheduled a site visit for you this Saturday. A representative will meet you at the property. I will message you details shortly.",
                "assertions": {
                  "buying_stage": "Ready to Schedule",
                  "intent": "schedule_visit"
                }
            }
        ]
    }

    # 6. Negotiation Started
    negotiation_json = {
        "name": "Negotiation Started",
        "description": "Michael Chang initiates a price negotiation.",
        "steps": [
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "Hello, I am interested in buying a 4-bedroom villa in Palm Jumeirah. Budget is $3.5 Million."
            },
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "The villa is great. Can we negotiate the price? I would like to offer $3.3 Million instead of $3.5 Million.",
                "mock_reply": "Thank you for the offer. I will discuss this $3.3 Million proposal directly with the developer and get back to you with terms.",
                "assertions": {
                  "buying_stage": "Negotiation",
                  "intent": "negotiation"
                }
            }
        ]
    }

    # 7. Booking Confirmed
    booking_json = {
        "name": "Booking Confirmed",
        "description": "Michael Chang confirms the booking agreement.",
        "steps": [
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "Hello, I am interested in buying a 4-bedroom villa in Palm Jumeirah. Budget is $3.5 Million."
            },
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "Great, I agree to the negotiated terms of $3.4 Million. Let's confirm the booking and proceed with the contract.",
                "mock_reply": "Perfect! Your booking is officially confirmed at $3.4 Million. I am initiating the sales contract paperwork now.",
                "assertions": {
                  "buying_stage": "Purchase Ready",
                  "intent": "booking_confirmation"
                }
            }
        ]
    }

    # 8. Lost Lead
    lost_json = {
        "name": "Lost Lead",
        "description": "A buyer halts search and requests closing the lead.",
        "steps": [
            {
                "sender": "customer",
                "name": "John Cold",
                "phone": "15125550234",
                "message": "Thanks for the details but we decided to put our search on hold. Please close our file.",
                "mock_reply": "Understood, John. I have updated your search file to inactive. Feel free to contact us whenever you're ready to search again.",
                "assertions": {
                  "buying_stage": "Research",
                  "intent": "unsubscribe"
                }
            }
        ]
    }

    # 9. Returning Buyer
    returning_json = {
        "name": "Returning Buyer",
        "description": "A previously closed buyer returns with a new inquiry.",
        "steps": [
            {
                "sender": "customer",
                "name": "Michael Chang",
                "phone": "13055550198",
                "message": "Hi, it's Michael again. The villa purchase was great. Now I'm looking to buy a rental apartment in Marina.",
                "mock_reply": "Welcome back Michael! It's great to hear from you again. I will search for high-yield rental investment apartments in Dubai Marina immediately.",
                "assertions": {
                  "buying_stage": "Research",
                  "intent": "inquiry",
                  "location": "Marina"
                }
            }
        ]
    }

    # 10. High Priority Buyer
    priority_json = {
        "name": "High Priority Buyer",
        "description": "Urgent luxury cash buyer requesting immediate response.",
        "steps": [
            {
                "sender": "customer",
                "name": "Elon Rich",
                "phone": "16505550888",
                "message": "I need to buy a luxury penthouse in Palm Jumeirah immediately. Budget is $15 Million cash. Contact me now.",
                "mock_reply": "Hello! I have flagged your request for our executive sales team. We have premium $15 Million penthouses in Palm Jumeirah, and a specialist will contact you in a few minutes.",
                "assertions": {
                  "buying_stage": "Purchase Ready",
                  "intent": "inquiry",
                  "location": "Palm Jumeirah"
                }
            }
        ]
    }

    # Write all JSON files
    templates = {
        "apartment_buyer.json": apartment_json,
        "villa_buyer.json": villa_json,
        "commercial_buyer.json": commercial_json,
        "budget_increase.json": budget_json,
        "site_visit.json": visit_json,
        "negotiation.json": negotiation_json,
        "booking_confirmed.json": booking_json,
        "lost_lead.json": lost_json,
        "returning_buyer.json": returning_json,
        "high_priority.json": priority_json
    }
    
    for filename, content in templates.items():
        filepath = scenarios_dir / filename
        if not filepath.exists():
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)

async def load_scenario_template(name: str) -> dict:
    """Load a scenario template JSON from the scenarios folder."""
    ensure_scenario_templates()
    filepath = get_scenarios_dir() / f"{name}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Scenario template {name} not found.")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

async def trigger_scenario_run(session: AsyncSession, name: str) -> List[dict]:
    """Load and execute all steps in a scenario template sequentially."""
    template = await load_scenario_template(name)
    steps = template.get("steps", [])
    results = []
    
    for step in steps:
        res = await run_scenario_step(session, name, step)
        results.append(res)
        # Small delay to keep execution realistic
        await asyncio.sleep(0.1)
        
    return results

async def time_travel(session: AsyncSession, seconds: int) -> Dict[str, Any]:
    """Advance the clock travel offset, scan, and execute pending jobs."""
    simulation_state.time_offset_seconds += seconds
    travel_time = SystemClock.now()
    
    # Write Audit log
    await write_audit_log(
        session=session,
        workspace_id=SIMULATION_WORKSPACE_ID,
        user_id=None,
        action="time_travel",
        target_type="system",
        payload={"offset_seconds_added": seconds, "new_simulated_time": travel_time.isoformat()}
    )
    
    # ── Job Execution Pass ──
    # Fetch background jobs scheduled at or before travel_time that are still pending
    q = select(BackgroundJob).where(
        BackgroundJob.status == JobStatus.pending,
        BackgroundJob.scheduled_at <= travel_time
    )
    result = await session.execute(q)
    pending_jobs = result.scalars().all()
    
    executed_jobs = []
    for job in pending_jobs:
        job.status = JobStatus.running
        job.started_at = travel_time
        await session.flush()
        
        # Simulate quick execution
        import random
        success = random.random() > 0.05  # 95% success rate
        if success:
            job.status = JobStatus.completed
            job.completed_at = travel_time + timedelta(milliseconds=150)
            details = "Completed successfully (Simulated)"
        else:
            job.status = JobStatus.failed
            job.completed_at = travel_time + timedelta(milliseconds=200)
            job.last_error = f"Database sync failed during execution pass."
            details = job.last_error
            
        await write_audit_log(
            session=session,
            workspace_id=job.workspace_id,
            user_id=None,
            action=f"execute_{job.job_type}",
            target_type="background_job",
            target_id=job.id,
            payload={"status": job.status.value, "last_error": job.last_error}
        )
        
        executed_event = {
            "timestamp": travel_time.isoformat(),
            "type": "time_machine_job_executed",
            "job_id": str(job.id),
            "job_type": job.job_type,
            "status": job.status.value,
            "details": details
        }
        simulation_state.active_timeline.append(executed_event)
        executed_jobs.append(executed_event)
        
    await session.commit()
    
    # Send WebSocket update
    try:
        from app.integrations.websocket.manager import ws_manager
        await ws_manager.broadcast({
            "event": "time_machine_travelled",
            "data": {
                "new_time": travel_time.isoformat(),
                "jobs_executed": len(executed_jobs)
            }
        })
    except Exception:
        pass

    return {
        "new_simulated_time": travel_time,
        "offset_total_seconds": simulation_state.time_offset_seconds,
        "jobs_processed_count": len(executed_jobs),
        "jobs_executed": executed_jobs
    }

async def reset_demo_data(session: AsyncSession, options: ResetSchema) -> Dict[str, Any]:
    """Safe cleanup of all objects flagged with is_demo = True."""
    stats = {}
    
    # 1. Reset Background Jobs
    if options.clear_queue or options.reset_everything:
        res = await session.execute(
            delete(BackgroundJob).where(BackgroundJob.is_demo == True)
        )
        stats["background_jobs_cleared"] = res.rowcount
        
    # 2. Reset Conversations (Messages, AIMetadata cascade automatically)
    if options.clear_conversations or options.reset_everything:
        res = await session.execute(
            delete(Conversation).where(Conversation.is_demo == True)
        )
        stats["conversations_cleared"] = res.rowcount
        
    # 3. Reset Customers (Memory, versions, events, and intents cascade automatically)
    if options.clear_buyers or options.reset_everything:
        res = await session.execute(
            delete(Customer).where(Customer.is_demo == True)
        )
        stats["customers_cleared"] = res.rowcount
        
    # 4. Reset Audit Logs
    if options.clear_audit_logs or options.reset_everything:
        res = await session.execute(
            delete(AuditLog).where(AuditLog.is_demo == True)
        )
        stats["audit_logs_cleared"] = res.rowcount
        
    if options.clear_activity or options.reset_everything:
        # Customer Memory Events cascade automatically when customer is deleted,
        # but if we just want to clear them explicitly while leaving customers:
        if not (options.clear_buyers or options.reset_everything):
            from app.domain.memory.models import CustomerMemoryEvent
            res = await session.execute(
                delete(CustomerMemoryEvent).where(
                    CustomerMemoryEvent.customer_id.in_(
                        select(Customer.id).where(Customer.is_demo == True)
                    )
                )
            )
            stats["memory_events_cleared"] = res.rowcount
            
    await session.commit()
    
    # Broadcast clear to dashboard WebSocket
    try:
        from app.integrations.websocket.manager import ws_manager
        await ws_manager.broadcast({
            "event": "demo_data_reset",
            "data": stats
        })
    except Exception:
        pass
        
    return stats

async def run_regression_suite(session: AsyncSession) -> Dict[str, Any]:
    """Execute all scenario templates and check database assertions."""
    ensure_scenario_templates()
    scenarios_dir = get_scenarios_dir()
    templates = [f.stem for f in scenarios_dir.glob("*.json")]
    
    total_passed = 0
    total_failed = 0
    categories = {}
    
    # We will run them using simulated AI
    prev_mock_ai = simulation_state.mock_ai
    simulation_state.mock_ai = True
    
    for template_name in templates:
        # Load template
        template = await load_scenario_template(template_name)
        steps = template.get("steps", [])
        
        # Categorize templates
        # Default categorizations based on template properties
        category = "AI & Message Flow"
        if "visit" in template_name or "booking" in template_name or "negotiation" in template_name:
            category = "CRM & Scheduling"
        elif "budget" in template_name or "priority" in template_name:
            category = "Intent Extraction"
        elif "lost" in template_name or "returning" in template_name:
            category = "Customer Memory"
            
        if category not in categories:
            categories[category] = []
            
        passed = True
        details = "Steps executed successfully."
        
        try:
            # Clear previous scenario state
            is_demo_context.set(True)
            
            # Execute steps
            for step in steps:
                # Dispatch step
                if "mock_reply" in step:
                    simulation_state.next_mock_reply = step["mock_reply"]
                    
                payload = build_simulated_payload(
                    channel="WhatsApp",
                    contact_name=step.get("name", "Sarah Jenkins"),
                    identifier=step.get("phone", "12025550143"),
                    message=step.get("message", "")
                )
                payload["workspace_id"] = str(SIMULATION_WORKSPACE_ID)
                
                await dispatch_webhook_payload(session, payload)
                
                # Check assertions
                assertions = step.get("assertions", {})
                if assertions:
                    # Query customer details
                    phone = step.get("phone")
                    q = select(Customer).where(Customer.phone == phone)
                    cust_result = await session.execute(q)
                    cust = cust_result.scalar_one_or_none()
                    
                    if not cust:
                        passed = False
                        details = f"Assertion failed: customer with phone {phone} was not created."
                        break
                        
                    # Check buying stage assertion
                    if "buying_stage" in assertions:
                        expected = assertions["buying_stage"]
                        if cust.buying_stage != expected:
                            passed = False
                            details = f"Assertion failed: buying stage was '{cust.buying_stage}', expected '{expected}'."
                            break
                            
                    # Check location extraction assertion
                    if "location" in assertions:
                        expected = assertions["location"]
                        # Fetch customer memory
                        from app.domain.memory.service import get_customer_memory
                        mem = await get_customer_memory(session, cust.id)
                        struct = mem.structured_data if mem else {}
                        location_val = struct.get("preferred_location", {}).get("value", "")
                        if expected.lower() not in location_val.lower():
                            passed = False
                            details = f"Assertion failed: preferred location was '{location_val}', expected to contain '{expected}'."
                            break
            
        except Exception as e:
            passed = False
            details = f"Exception encountered: {str(e)}"
            
        if passed:
            total_passed += 1
        else:
            total_failed += 1
            
        categories[category].append({
            "name": template.get("name", template_name),
            "passed": passed,
            "details": details
        })
        
    simulation_state.mock_ai = prev_mock_ai
    
    # Construct results schemas
    results = []
    for cat_name, cases in categories.items():
        passed_cnt = sum(1 for c in cases if c["passed"])
        failed_cnt = sum(1 for c in cases if not c["passed"])
        results.append({
            "category": cat_name,
            "passed": passed_cnt,
            "failed": failed_cnt,
            "test_cases": cases
        })
        
    return {
        "timestamp": datetime.now(timezone.utc),
        "success": total_failed == 0,
        "summary": {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_run": total_passed + total_failed
        },
        "results": results
    }

async def get_performance_metrics(session: AsyncSession) -> Dict[str, Any]:
    """Calculate system statistics and rolling database query metrics."""
    # Virtual CPU & RAM usage
    cpu_usage = 12.5
    ram_usage = 42.1
    
    try:
        import psutil
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
    except ImportError:
        pass
        
    # Database latency check
    t0 = time.monotonic()
    await session.execute(select(1))
    db_latency = int((time.monotonic() - t0) * 1000)
    
    if simulation_state.database_status == "slow":
        db_latency += 2000
        
    # Average Response time & Token usage
    q = select(
        func.avg(AIMetadata.latency_ms).label("avg_latency"),
        func.sum(AIMetadata.total_tokens).label("total_tokens"),
        func.avg(AIMetadata.total_tokens).label("avg_tokens")
    )
    res = await session.execute(q)
    row = res.one_or_none()
    
    avg_latency = float(row.avg_latency) if row and row.avg_latency else 180.0
    total_tokens = int(row.total_tokens) if row and row.total_tokens else 12500
    avg_tokens = float(row.avg_tokens) if row and row.avg_tokens else 240.0
    
    # WebSocket throughput - simulated rolling counts
    websocket_throughput = len(simulation_state.active_timeline)
    
    return {
        "cpu_usage_pct": cpu_usage,
        "ram_usage_pct": ram_usage,
        "db_latency_ms": db_latency,
        "avg_api_latency_ms": avg_latency,
        "total_token_usage": total_tokens,
        "avg_token_usage_per_response": avg_tokens,
        "websocket_throughput": websocket_throughput
    }
