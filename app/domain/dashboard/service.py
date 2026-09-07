"""
dashboard_service — All query logic for the Live Dashboard.

Public API:
    get_overview_metrics(session, workspace_id) -> OverviewMetrics
    get_conversations(session, workspace_id, filters, page, page_size) -> ConversationPage
    get_conversation_detail(session, conversation_id) -> ConversationDetail
    get_customers(session, workspace_id, filters, page, page_size) -> CustomerPage
    get_customer_profile(session, workspace_id, customer_id) -> CustomerProfile
    update_customer(session, customer_id, req, actor_user_id) -> None
    get_analytics(session, workspace_id, date_from, date_to) -> AnalyticsData
    get_system_health(session) -> SystemHealth
    get_activity_feed(session, workspace_id, limit) -> list[ActivityEvent]
    get_lead_pipeline(session, workspace_id) -> LeadPipeline
    update_lead_stage(session, customer_id, stage, actor_user_id, reason) -> None
    search_everything(session, workspace_id, query, limit) -> SearchResults
    get_queue_status(session, workspace_id) -> QueueStatus
    get_audit_log(session, workspace_id, limit) -> list[AuditLogSchema]
    write_audit_log(session, workspace_id, user_id, action, ...) -> None
    authenticate_user(session, email, password) -> User | None
    create_access_token(user) -> str
    get_user_from_token(session, token) -> User | None
"""

import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import case, func, select, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.domain.conversations.models import AIMetadata, Conversation, Message, MessageDirection
from app.domain.customers.models import Customer, CustomerStatus
from app.domain.dashboard.models import (
    BackgroundJob,
    JobStatus,
    PipelineEvent,
)
from app.domain.security.models import (
    AuditLog,
    User,
    UserRole,
    DEFAULT_WORKSPACE_ID,
)
from app.domain.security.engines.authorization import role_can
from app.domain.dashboard.schemas import (
    ActivityEvent,
    AnalyticsData,
    AuditLogSchema,
    BackgroundJobSchema,
    ConversationDetail,
    ConversationPage,
    ConversationSummary,
    CostMetrics,
    CustomerPage,
    CustomerProfile,
    CustomerSummary,
    DailyMetric,
    IntentDistribution,
    IntentSummary,
    LeadCard,
    LeadPipeline,
    MemorySummary,
    MessageDetail,
    MetricCard,
    OverviewMetrics,
    PipelineEventSchema,
    QueueStatus,
    SearchHit,
    SearchResults,
    ServiceStatus,
    SystemHealth,
)
from app.domain.intent.models import IntentHistory
from app.domain.leads.service import qualify_lead, _score_to_grade
from app.domain.memory.models import CustomerMemory, CustomerMemoryEvent
from app.utils.logger import get_logger
from app.utils.context import is_demo_context
from app.utils.clock import SystemClock

logger = get_logger(__name__)

# ── Auth helpers ──────────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480   # 8 hours


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(password, user.password_hash):
        return None
    user.last_login = datetime.now(timezone.utc)
    await session.flush()
    return user


def create_access_token(user: User) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "workspace_id": str(user.workspace_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.dashboard_secret_key, algorithm=ALGORITHM)


async def get_user_from_token(
    session: AsyncSession,
    token: str,
) -> Optional[User]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.dashboard_secret_key, algorithms=[ALGORITHM])
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ── Overview ──────────────────────────────────────────────────────────────────

async def get_overview_metrics(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
) -> OverviewMetrics:
    """Compute all 9 KPI cards in a minimal number of DB queries."""
    today_start = SystemClock.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Total customers
    total_customers = await session.scalar(select(func.count(Customer.id)).where(Customer.workspace_id == workspace_id))

    # New leads today (customers created today)
    new_today = await session.scalar(
        select(func.count(Customer.id)).where(Customer.workspace_id == workspace_id, Customer.created_at >= today_start)
    )

    # Qualified leads (buying_stage not null and not Research)
    qualified = await session.scalar(
        select(func.count(Customer.id)).where(
            Customer.workspace_id == workspace_id,
            Customer.buying_stage != "Research",
            Customer.buying_stage.is_not(None)
        )
    )

    # Purchase ready
    purchase_ready = await session.scalar(
        select(func.count(Customer.id)).where(
            Customer.workspace_id == workspace_id,
            Customer.buying_stage == "Purchase Ready"
        )
    )

    # Active conversations (those with messages in last 24h)
    cutoff = SystemClock.now() - timedelta(hours=24)
    active_convos = await session.scalar(
        select(func.count(func.distinct(Message.conversation_id)))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.workspace_id == workspace_id,
            Message.timestamp >= cutoff
        )
    )

    # Avg response time (from ai_metadata latency)
    avg_latency = await session.scalar(
        select(func.avg(AIMetadata.latency_ms))
        .join(Message, AIMetadata.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.workspace_id == workspace_id,
            AIMetadata.latency_ms.isnot(None)
        )
    )

    # AI success rate (rows with finish_reason = "stop")
    total_ai = await session.scalar(
        select(func.count(AIMetadata.id))
        .join(Message, AIMetadata.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.workspace_id == workspace_id)
    )
    success_ai = await session.scalar(
        select(func.count(AIMetadata.id))
        .join(Message, AIMetadata.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.workspace_id == workspace_id,
            AIMetadata.finish_reason == "stop"
        )
    )
    success_rate = round((success_ai / total_ai * 100) if total_ai else 100.0, 1)

    # Memory updates today
    mem_updates = await session.scalar(
        select(func.count(CustomerMemoryEvent.id))
        .join(Customer, CustomerMemoryEvent.customer_id == Customer.id)
        .where(
            Customer.workspace_id == workspace_id,
            CustomerMemoryEvent.created_at >= today_start,
            CustomerMemoryEvent.event_type == "memory_summarized",
        )
    )

    # Cost today
    cost_today = await session.scalar(
        select(func.sum(AIMetadata.estimated_cost_usd)).join(
            Message, AIMetadata.message_id == Message.id
        ).join(Conversation, Message.conversation_id == Conversation.id).where(
            Conversation.workspace_id == workspace_id,
            Message.timestamp >= today_start
        )
    )

    # Scheduling Metrics (Phase 5)
    from app.domain.scheduling.models import ScheduledEvent
    upcoming_events = await session.scalar(
        select(func.count(ScheduledEvent.id))
        .join(Customer, ScheduledEvent.customer_id == Customer.id)
        .where(
            Customer.workspace_id == workspace_id,
            ScheduledEvent.status.in_(["pending", "confirmed"]),
            ScheduledEvent.scheduled_for >= today_start
        )
    )
    pending_callbacks = await session.scalar(
        select(func.count(ScheduledEvent.id))
        .join(Customer, ScheduledEvent.customer_id == Customer.id)
        .where(
            Customer.workspace_id == workspace_id,
            ScheduledEvent.status == "pending",
            ScheduledEvent.event_type == "callback"
        )
    )

    # Follow-up Metrics (Phase 6)
    from app.domain.followup.models import FollowUpQueue
    pending_followups = await session.scalar(
        select(func.count(FollowUpQueue.id))
        .join(Customer, FollowUpQueue.customer_id == Customer.id)
        .where(
            Customer.workspace_id == workspace_id,
            FollowUpQueue.status.in_(["scheduled", "executing"])
        )
    )

    def card(label, value, unit=None, trend=None, direction=None) -> MetricCard:
        return MetricCard(
            label=label,
            value=value or 0,
            unit=unit,
            trend=trend,
            trend_direction=direction,
        )

    return OverviewMetrics(
        active_conversations=card("Active Conversations", active_convos or 0),
        total_customers=card("Total Customers", total_customers or 0),
        new_leads_today=card("New Leads Today", new_today or 0),
        qualified_leads=card("Qualified Leads", qualified or 0),
        purchase_ready=card("Purchase Ready", purchase_ready or 0),
        avg_response_time_ms=card("Avg Response Time", int(avg_latency or 0), unit="ms"),
        ai_success_rate=card("AI Success Rate", success_rate, unit="%"),
        memory_updates_today=card("Memory Updates Today", mem_updates or 0),
        total_cost_today_usd=card("AI Cost Today", round(float(cost_today or 0), 4), unit="USD"),
        upcoming_events=card("Upcoming Events", upcoming_events or 0),
        pending_callbacks=card("Pending Callbacks", pending_callbacks or 0),
        pending_followups=card("Pending Follow-ups", pending_followups or 0),
    )


# ── Conversations ─────────────────────────────────────────────────────────────

async def get_conversations(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
    search: Optional[str] = None,
    buying_stage: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> ConversationPage:
    base_q = (
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.customer))
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.created_at.desc())
    )

    if search:
        base_q = base_q.join(Customer, Conversation.customer_id == Customer.id).where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
                Conversation.customer_phone.ilike(f"%{search}%"),
            )
        )
    if buying_stage:
        base_q = base_q.join(Customer, Conversation.customer_id == Customer.id, isouter=True).where(
            Customer.buying_stage == buying_stage
        )

    total = await session.scalar(select(func.count()).select_from(base_q.subquery()))
    offset = (page - 1) * page_size
    result = await session.execute(base_q.offset(offset).limit(page_size))
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        last_msg = conv.messages[-1] if conv.messages else None
        # Fetch latest intent for this conversation
        intent_row = await session.scalar(
            select(IntentHistory)
            .where(IntentHistory.conversation_id == conv.id)
            .order_by(IntentHistory.created_at.desc())
            .limit(1)
        )
        items.append(ConversationSummary(
            id=conv.id,
            customer_id=conv.customer_id,
            customer_name=conv.customer.name if conv.customer else None,
            customer_phone=conv.customer_phone,
            last_message=last_msg.content[:120] if last_msg else None,
            last_message_direction=last_msg.direction.value if last_msg else None,
            last_activity=last_msg.timestamp if last_msg else conv.created_at,
            message_count=len(conv.messages),
            detected_intent=str(intent_row.detected_intent) if intent_row else None,
            buying_stage=conv.customer.buying_stage if conv.customer else None,
            urgency=str(intent_row.urgency) if intent_row else None,
            created_at=conv.created_at,
        ))

    return ConversationPage(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < (total or 0),
    )


async def get_conversation_detail(
    session: AsyncSession,
    conversation_id: UUID,
    workspace_id: UUID,
) -> Optional[ConversationDetail]:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.workspace_id == workspace_id)
        .options(
            selectinload(Conversation.messages).selectinload(Message.ai_metadata),
            selectinload(Conversation.messages).selectinload(Message.intent_history),
            selectinload(Conversation.messages).selectinload(Message.pipeline_events),
            selectinload(Conversation.customer),
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return None

    messages_detail = []
    all_pipeline_events = []

    for msg in conv.messages:
        intent = msg.intent_history
        meta = msg.ai_metadata

        intent_summary = None
        if intent:
            intent_summary = IntentSummary(
                detected_intent=str(intent.detected_intent),
                confidence=float(intent.confidence),
                urgency=str(intent.urgency),
                buying_stage=intent.buying_stage,
                budget=intent.budget,
                budget_confidence=float(intent.budget_confidence) if intent.budget_confidence else None,
                timeline=intent.timeline,
                interest=intent.interest,
                location=intent.location,
                next_action=intent.next_action,
                reasoning=intent.reasoning,
                memory_influenced=intent.memory_influenced,
                detected_keywords=intent.detected_keywords,
                created_at=intent.created_at,
            )

        messages_detail.append(MessageDetail(
            id=msg.id,
            direction=msg.direction.value,
            content=msg.content,
            timestamp=msg.timestamp,
            intent=intent_summary,
            ai_model=meta.model if meta else None,
            total_tokens=meta.total_tokens if meta else None,
            latency_ms=meta.latency_ms if meta else None,
            estimated_cost_usd=float(meta.estimated_cost_usd) if meta and meta.estimated_cost_usd else None,
        ))

        for pe in (msg.pipeline_events or []):
            all_pipeline_events.append(PipelineEventSchema(
                id=pe.id,
                step=pe.step.value if hasattr(pe.step, "value") else str(pe.step),
                status=pe.status,
                duration_ms=pe.duration_ms,
                payload=pe.payload,
                created_at=pe.created_at,
            ))

    return ConversationDetail(
        id=conv.id,
        customer_id=conv.customer_id,
        customer_name=conv.customer.name if conv.customer else None,
        customer_phone=conv.customer_phone,
        created_at=conv.created_at,
        messages=messages_detail,
        pipeline_events=sorted(all_pipeline_events, key=lambda x: x.created_at),
    )


# ── Customers ─────────────────────────────────────────────────────────────────

async def get_customers(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
    search: Optional[str] = None,
    buying_stage: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> CustomerPage:
    q = select(Customer).where(Customer.workspace_id == workspace_id).order_by(Customer.created_at.desc())

    if search:
        q = q.where(or_(
            Customer.name.ilike(f"%{search}%"),
            Customer.phone.ilike(f"%{search}%"),
            Customer.email.ilike(f"%{search}%"),
        ))
    if buying_stage:
        q = q.where(Customer.buying_stage == buying_stage)
    if status:
        q = q.where(Customer.status == status)

    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    result = await session.execute(q.offset((page - 1) * page_size).limit(page_size))
    customers = result.scalars().all()

    items = []
    for cust in customers:
        qual = await qualify_lead(session, cust.id, None)
        items.append(CustomerSummary(
            id=cust.id,
            name=cust.name,
            phone=cust.phone,
            email=cust.email,
            status=str(cust.status.value) if hasattr(cust.status, "value") else str(cust.status),
            buying_stage=cust.buying_stage,
            qualification_score=qual["score"] if qual else None,
            qualification_grade=qual["grade"] if qual else None,
            last_interaction=cust.last_interaction,
            created_at=cust.created_at,
        ))

    return CustomerPage(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < (total or 0),
    )


async def get_customer_profile(
    session: AsyncSession,
    customer_id: UUID,
    workspace_id: UUID,
) -> Optional[CustomerProfile]:
    result = await session.execute(
        select(Customer)
        .where(Customer.id == customer_id, Customer.workspace_id == workspace_id)
        .options(selectinload(Customer.memory))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        return None

    # Memory
    mem = customer.memory
    memory_summary = None
    if mem:
        structured = mem.structured_data or {}
        memory_summary = MemorySummary(
            summary=mem.summary,
            budget=structured.get("budget"),
            timeline=structured.get("timeline"),
            preferred_location=structured.get("preferred_location"),
            interests=structured.get("interests"),
            message_count=mem.message_count,
            last_updated=mem.last_updated,
        )

    # Recent intents
    intent_rows = await session.execute(
        select(IntentHistory)
        .where(IntentHistory.customer_id == customer_id)
        .order_by(IntentHistory.created_at.desc())
        .limit(5)
    )
    recent_intents = [
        IntentSummary(
            detected_intent=str(ih.detected_intent),
            confidence=float(ih.confidence),
            urgency=str(ih.urgency),
            buying_stage=ih.buying_stage,
            budget=ih.budget,
            budget_confidence=float(ih.budget_confidence) if ih.budget_confidence else None,
            timeline=ih.timeline,
            interest=ih.interest,
            location=ih.location,
            next_action=ih.next_action,
            reasoning=ih.reasoning,
            memory_influenced=ih.memory_influenced,
            detected_keywords=ih.detected_keywords,
            created_at=ih.created_at,
        )
        for ih in intent_rows.scalars().all()
    ]

    # Conversation count
    conv_count = await session.scalar(
        select(func.count(Conversation.id)).where(Conversation.customer_id == customer_id)
    )

    # Qualification
    qual = await qualify_lead(session, customer_id, None)

    return CustomerProfile(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        status=str(customer.status.value) if hasattr(customer.status, "value") else str(customer.status),
        buying_stage=customer.buying_stage,
        notes=customer.notes,
        preferred_language=customer.preferred_language,
        created_at=customer.created_at,
        last_interaction=customer.last_interaction,
        memory=memory_summary,
        recent_intents=recent_intents,
        conversation_count=conv_count or 0,
        qualification=qual,
    )


async def update_customer(
    session: AsyncSession,
    customer_id: UUID,
    updates: dict,
    actor_user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    workspace_id: Optional[UUID] = None,
) -> None:
    result = await session.execute(select(Customer).where(Customer.id == customer_id, Customer.workspace_id == workspace_id))
    customer = result.scalar_one_or_none()
    if not customer:
        return

    before = {k: getattr(customer, k, None) for k in updates}
    for key, val in updates.items():
        if hasattr(customer, key) and val is not None:
            setattr(customer, key, val)
    await session.flush()

    # Write audit log
    await write_audit_log(
        session=session,
        workspace_id=workspace_id or DEFAULT_WORKSPACE_ID,
        user_id=actor_user_id,
        action="update_customer",
        target_type="customer",
        target_id=customer_id,
        payload={"before": {k: str(v) if v else None for k, v in before.items()},
                 "after": {k: str(v) if v else None for k, v in updates.items()}},
        ip_address=ip_address,
    )


# ── Leads ─────────────────────────────────────────────────────────────────────

LEAD_STAGES = [
    "Research",
    "Comparing Options",
    "Ready to Schedule",
    "Negotiation",
    "Purchase Ready",
]


async def get_lead_pipeline(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
) -> LeadPipeline:
    result = await session.execute(
        select(Customer).where(Customer.workspace_id == workspace_id, Customer.buying_stage.isnot(None))
    )
    customers = result.scalars().all()

    stages: dict[str, list[LeadCard]] = {s: [] for s in LEAD_STAGES}

    for cust in customers:
        stage = cust.buying_stage or "Research"
        if stage not in stages:
            stages[stage] = []

        latest_intent = await session.scalar(
            select(IntentHistory)
            .where(IntentHistory.customer_id == cust.id)
            .order_by(IntentHistory.created_at.desc())
            .limit(1)
        )

        qual = await qualify_lead(session, cust.id, None)
        score = qual["score"] if qual else 0
        grade = qual["grade"] if qual else "F"

        stages[stage].append(LeadCard(
            customer_id=cust.id,
            name=cust.name,
            phone=cust.phone,
            buying_stage=stage,
            urgency=str(latest_intent.urgency) if latest_intent else None,
            budget=latest_intent.budget if latest_intent else None,
            timeline=latest_intent.timeline if latest_intent else None,
            interest=latest_intent.interest if latest_intent else None,
            qualification_score=score,
            qualification_grade=grade,
            last_interaction=cust.last_interaction,
        ))

    return LeadPipeline(stages=stages)


async def update_lead_stage(
    session: AsyncSession,
    customer_id: UUID,
    new_stage: str,
    actor_user_id: Optional[UUID] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    workspace_id: Optional[UUID] = None,
) -> None:
    result = await session.execute(select(Customer).where(Customer.id == customer_id, Customer.workspace_id == workspace_id))
    customer = result.scalar_one_or_none()
    if not customer:
        return

    old_stage = customer.buying_stage
    customer.buying_stage = new_stage
    await session.flush()

    await write_audit_log(
        session=session,
        workspace_id=workspace_id or DEFAULT_WORKSPACE_ID,
        user_id=actor_user_id,
        action="change_lead_stage",
        target_type="customer",
        target_id=customer_id,
        payload={"before": {"buying_stage": old_stage},
                 "after": {"buying_stage": new_stage},
                 "reason": reason},
        ip_address=ip_address,
    )


# ── Analytics ─────────────────────────────────────────────────────────────────

async def get_analytics(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> AnalyticsData:
    if not date_from:
        date_from = (SystemClock.now() - timedelta(days=30)).date()
    if not date_to:
        date_to = SystemClock.now().date()

    from_dt = datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc)
    to_dt   = datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Conversations per day
    conv_rows = await session.execute(
        select(
            func.date(Conversation.created_at).label("day"),
            func.count(Conversation.id).label("cnt"),
        )
        .where(Conversation.workspace_id == workspace_id, Conversation.created_at.between(from_dt, to_dt))
        .group_by(text("day"))
        .order_by(text("day"))
    )
    convs_per_day = [
        DailyMetric(date=str(row.day), value=row.cnt)
        for row in conv_rows.all()
    ]

    # Leads per day (new customers)
    lead_rows = await session.execute(
        select(
            func.date(Customer.created_at).label("day"),
            func.count(Customer.id).label("cnt"),
        )
        .where(Customer.workspace_id == workspace_id, Customer.created_at.between(from_dt, to_dt))
        .group_by(text("day"))
        .order_by(text("day"))
    )
    leads_per_day = [
        DailyMetric(date=str(row.day), value=row.cnt)
        for row in lead_rows.all()
    ]

    # Intent distribution
    intent_rows = await session.execute(
        select(
            IntentHistory.detected_intent,
            func.count(IntentHistory.id).label("cnt"),
        )
        .where(IntentHistory.workspace_id == workspace_id, IntentHistory.created_at.between(from_dt, to_dt))
        .group_by(IntentHistory.detected_intent)
        .order_by(func.count(IntentHistory.id).desc())
    )
    total_intents = sum(r.cnt for r in intent_rows.all()) or 1
    intent_rows = await session.execute(
        select(IntentHistory.detected_intent, func.count(IntentHistory.id).label("cnt"))
        .where(IntentHistory.workspace_id == workspace_id, IntentHistory.created_at.between(from_dt, to_dt))
        .group_by(IntentHistory.detected_intent)
        .order_by(func.count(IntentHistory.id).desc())
    )
    intent_dist = [
        IntentDistribution(
            intent=str(r.detected_intent),
            count=r.cnt,
            percentage=round(r.cnt / total_intents * 100, 1),
        )
        for r in intent_rows.all()
    ]

    # Avg response time per day
    latency_rows = await session.execute(
        select(
            func.date(Message.timestamp).label("day"),
            func.avg(AIMetadata.latency_ms).label("avg_ms"),
        )
        .join(AIMetadata, AIMetadata.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.workspace_id == workspace_id, Message.timestamp.between(from_dt, to_dt))
        .group_by(text("day"))
        .order_by(text("day"))
    )
    latency_per_day = [
        DailyMetric(date=str(row.day), value=round(float(row.avg_ms or 0)))
        for row in latency_rows.all()
    ]

    # Cost metrics
    cost_agg = await session.execute(
        select(
            func.sum(AIMetadata.estimated_cost_usd).label("total_cost"),
            func.sum(AIMetadata.prompt_tokens).label("total_prompt"),
            func.sum(AIMetadata.completion_tokens).label("total_completion"),
            func.avg(AIMetadata.total_tokens).label("avg_tokens"),
            func.count(AIMetadata.id).label("total_calls"),
        )
        .join(Message, AIMetadata.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.workspace_id == workspace_id, Message.timestamp.between(from_dt, to_dt))
    )
    cost_row = cost_agg.first()
    total_cost  = float(cost_row.total_cost or 0)
    total_calls = cost_row.total_calls or 1
    total_customers_period = await session.scalar(
        select(func.count(Customer.id)).where(Customer.workspace_id == workspace_id, Customer.created_at.between(from_dt, to_dt))
    ) or 1
    qualified_period = await session.scalar(
        select(func.count(Customer.id)).where(
            Customer.workspace_id == workspace_id,
            Customer.created_at.between(from_dt, to_dt),
            Customer.buying_stage.notin_(["Research", None]),
        )
    ) or 1

    cost_metrics = CostMetrics(
        total_cost_usd=round(total_cost, 6),
        avg_cost_per_conversation=round(total_cost / total_calls, 6),
        avg_cost_per_lead=round(total_cost / total_customers_period, 6),
        avg_cost_per_qualified_lead=round(total_cost / qualified_period, 6),
        total_prompt_tokens=int(cost_row.total_prompt or 0),
        total_completion_tokens=int(cost_row.total_completion or 0),
        avg_tokens_per_response=round(float(cost_row.avg_tokens or 0), 1),
    )

    return AnalyticsData(
        date_from=str(date_from),
        date_to=str(date_to),
        conversations_per_day=convs_per_day,
        leads_per_day=leads_per_day,
        intent_distribution=intent_dist,
        avg_response_time_per_day=latency_per_day,
        cost_metrics=cost_metrics,
    )


# ── System Health ─────────────────────────────────────────────────────────────

async def get_system_health(session: AsyncSession) -> SystemHealth:
    services = []

    # Database
    try:
        t0 = time.monotonic()
        await session.execute(text("SELECT 1"))
        db_latency = int((time.monotonic() - t0) * 1000)
        services.append(ServiceStatus(
            name="PostgreSQL", status="online", latency_ms=db_latency
        ))
    except Exception as e:
        services.append(ServiceStatus(name="PostgreSQL", status="offline", detail=str(e)))

    # OpenAI (lightweight check — just settings presence)
    settings = get_settings()
    if settings.openai_api_key:
        services.append(ServiceStatus(name="OpenAI API", status="online"))
    else:
        services.append(ServiceStatus(name="OpenAI API", status="offline", detail="API key not configured"))

    # WhatsApp
    if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
        services.append(ServiceStatus(name="WhatsApp Cloud API", status="online"))
    else:
        services.append(ServiceStatus(name="WhatsApp Cloud API", status="warning", detail="Credentials incomplete"))

    # Not-yet-configured services
    for svc in ["Redis", "Background Workers", "Email Provider"]:
        services.append(ServiceStatus(name=svc, status="not_configured"))

    overall = "healthy"
    if any(s.status == "offline" for s in services):
        overall = "down"
    elif any(s.status == "warning" for s in services):
        overall = "degraded"

    return SystemHealth(
        overall=overall,
        services=services,
        checked_at=datetime.now(timezone.utc),
    )


# ── Activity Feed ─────────────────────────────────────────────────────────────

async def get_activity_feed(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
    limit: int = 50,
) -> list[ActivityEvent]:
    result = await session.execute(
        select(CustomerMemoryEvent)
        .join(Customer, CustomerMemoryEvent.customer_id == Customer.id)
        .where(Customer.workspace_id == workspace_id)
        .order_by(CustomerMemoryEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    feed = []
    for ev in events:
        cust = await session.scalar(
            select(Customer).where(Customer.id == ev.customer_id)
        )
        event_type = str(ev.event_type.value) if hasattr(ev.event_type, "value") else str(ev.event_type)
        descriptions = {
            "customer_created": "New customer registered",
            "memory_summarized": "Customer memory updated",
            "budget_detected": "Budget signal detected",
            "timeline_detected": "Purchase timeline detected",
            "interest_detected": "Interest detected",
            "location_detected": "Location preference detected",
            "conversation_started": "New conversation started",
        }
        feed.append(ActivityEvent(
            id=ev.id,
            event_type=event_type,
            description=descriptions.get(event_type, event_type.replace("_", " ").title()),
            customer_name=cust.name if cust else None,
            customer_phone=cust.phone if cust else None,
            metadata=ev.payload,
            created_at=ev.created_at,
        ))

    return feed


# ── Queue Monitor ─────────────────────────────────────────────────────────────

async def get_queue_status(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
) -> QueueStatus:
    today_start = SystemClock.now().replace(hour=0, minute=0, second=0, microsecond=0)

    pending  = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.status == JobStatus.pending))
    running  = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.status == JobStatus.running))
    failed   = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.status == JobStatus.failed))
    done_today = await session.scalar(
        select(func.count(BackgroundJob.id)).where(
            BackgroundJob.workspace_id == workspace_id,
            BackgroundJob.status == JobStatus.completed,
            BackgroundJob.completed_at >= today_start,
        )
    )

    recent_jobs_result = await session.execute(
        select(BackgroundJob).where(BackgroundJob.workspace_id == workspace_id).order_by(BackgroundJob.scheduled_at.desc()).limit(20)
    )
    jobs = [BackgroundJobSchema.model_validate(j) for j in recent_jobs_result.scalars().all()]

    return QueueStatus(
        pending=pending or 0,
        running=running or 0,
        completed_today=done_today or 0,
        failed=failed or 0,
        jobs=jobs,
    )


# ── Audit Log ─────────────────────────────────────────────────────────────────

async def write_audit_log(
    session: AsyncSession,
    workspace_id: UUID,
    user_id: Optional[UUID],
    action: str,
    target_type: str,
    target_id: Optional[UUID] = None,
    payload: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    log = AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
        ip_address=ip_address,
        is_demo=is_demo_context.get(),
        created_at=datetime.now(timezone.utc),
    )
    session.add(log)
    await session.flush()


async def create_background_job(
    session: AsyncSession,
    job_type: str,
    status: JobStatus = JobStatus.pending,
    run_count: int = 0,
    last_error: Optional[str] = None,
    job_metadata: Optional[dict] = None,
    scheduled_at: Optional[datetime] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    workspace_id: Optional[UUID] = None,
) -> BackgroundJob:
    job = BackgroundJob(
        workspace_id=workspace_id or DEFAULT_WORKSPACE_ID,
        job_type=job_type,
        status=status,
        run_count=run_count,
        last_error=last_error,
        job_metadata=job_metadata,
        scheduled_at=scheduled_at or SystemClock.now(),
        started_at=started_at,
        completed_at=completed_at,
        is_demo=is_demo_context.get(),
    )
    session.add(job)
    await session.flush()
    return job


async def get_audit_log(
    session: AsyncSession,
    workspace_id: Optional[UUID] = None,
    limit: int = 100,
) -> list[AuditLogSchema]:
    q = select(AuditLog).where(AuditLog.workspace_id == workspace_id).order_by(AuditLog.created_at.desc()).limit(limit)
    result = await session.execute(q)
    logs = result.scalars().all()

    out = []
    for log in logs:
        user_email = None
        if log.user_id:
            u = await session.scalar(select(User).where(User.id == log.user_id))
            user_email = u.email if u else None
        out.append(AuditLogSchema(
            id=log.id,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            user_email=user_email,
            payload=log.payload,
            ip_address=log.ip_address,
            created_at=log.created_at,
        ))
    return out


# ── Search Everything ─────────────────────────────────────────────────────────

async def search_everything(
    session: AsyncSession,
    query: str,
    workspace_id: Optional[UUID] = None,
    limit: int = 30,
) -> SearchResults:
    """
    Unified text search across customers, conversations, memory, and intents.
    Uses ILIKE for compatibility — upgrade to pg_trgm or pg_vector in a future phase.
    """
    hits: list[SearchHit] = []

    if not query or len(query) < 2:
        return SearchResults(query=query, total=0, hits=[])

    pattern = f"%{query}%"

    # ── Customers ─────────────────────────────────────────────────────────────
    customer_rows = await session.execute(
        select(Customer).where(
            Customer.workspace_id == workspace_id,
            or_(
                Customer.name.ilike(pattern),
                Customer.phone.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.notes.ilike(pattern),
            )
        ).limit(10)
    )
    for c in customer_rows.scalars().all():
        hits.append(SearchHit(
            type="customer",
            id=c.id,
            title=c.name or c.phone,
            subtitle=c.phone,
            highlight=c.notes[:100] if c.notes and query.lower() in (c.notes or "").lower() else None,
            score=1.0,
        ))

    # ── Messages ──────────────────────────────────────────────────────────────
    msg_rows = await session.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.workspace_id == workspace_id, Message.content.ilike(pattern))
        .order_by(Message.timestamp.desc())
        .limit(10)
    )
    for m in msg_rows.scalars().all():
        conv = await session.scalar(select(Conversation).where(Conversation.id == m.conversation_id))
        hits.append(SearchHit(
            type="conversation",
            id=m.conversation_id,
            title=f"Conversation — {conv.customer_phone if conv else '?'}",
            subtitle=m.timestamp.strftime("%Y-%m-%d %H:%M"),
            highlight=m.content[:120],
            score=0.9,
        ))

    # ── Intent ────────────────────────────────────────────────────────────────
    intent_rows = await session.execute(
        select(IntentHistory).where(
            IntentHistory.workspace_id == workspace_id,
            or_(
                IntentHistory.reasoning.ilike(pattern),
                IntentHistory.budget.ilike(pattern),
                IntentHistory.interest.ilike(pattern),
                IntentHistory.location.ilike(pattern),
            )
        ).order_by(IntentHistory.created_at.desc()).limit(10)
    )
    for ih in intent_rows.scalars().all():
        hits.append(SearchHit(
            type="intent",
            id=ih.id,
            title=f"Intent: {ih.detected_intent}",
            subtitle=f"Confidence: {float(ih.confidence):.0%}",
            highlight=ih.reasoning[:120] if ih.reasoning else None,
            score=0.8,
        ))

    hits.sort(key=lambda h: h.score, reverse=True)
    return SearchResults(query=query, total=len(hits), hits=hits[:limit])


async def log_pipeline_step(
    session: AsyncSession,
    message_id: UUID,
    step: str,
    status: str = "success",
    duration_ms: Optional[int] = None,
    payload: Optional[dict] = None,
    workspace_id: Optional[UUID] = None,
) -> None:
    """
    Log a single execution step of the message processing pipeline.

    Used by dashboard's Event Replay trace playback panel.

    Args:
        session:      Active async database session.
        message_id:   Message row UUID that triggered this pipeline execution.
        step:         PipelineStep name (e.g. "message_received").
        status:       "success" or "error".
        duration_ms:  Latency of this step in milliseconds.
        payload:      Snapshotted data values of this step's output.
        workspace_id: Multi-tenancy filter.
    """
    from app.domain.dashboard.models import PipelineEvent, PipelineStep

    # Clean the step name if string passed
    try:
        step_val = PipelineStep(step)
    except ValueError:
        step_val = PipelineStep.error

    event = PipelineEvent(
        message_id=message_id,
        workspace_id=workspace_id or DEFAULT_WORKSPACE_ID,
        step=step_val,
        status=status,
        duration_ms=duration_ms,
        payload=payload,
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    await session.flush()
    logger.debug(
        "pipeline_step_logged",
        message_id=str(message_id),
        step=step,
        status=status,
    )

