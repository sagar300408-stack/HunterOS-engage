from app.domain.timeline.repository import TimelineRepository
from app.domain.timeline.service import TimelineProjection
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.service import AnalyticsProjection
from app.domain.livestream.service import LiveStreamProjection

from app.events.bus.registry import ConsumerRegistry
from app.events.projections.manager import ProjectionManager


def bootstrap_event_consumers(registry: ConsumerRegistry):
    """
    Central bootstrap location for registering all operational and projection consumers 
    with the HunterOS Consumer Registry.
    """
    def _register(consumer):
        # Dynamically register based on the consumer's subscriptions
        for event_class in consumer.get_subscriptions():
            registry.register(event_class, consumer)
            
    # 1. Register Projection Framework (Priority 50)
    projection_manager = ProjectionManager()
    
    #   1a. Timeline Projection
    timeline_repo = TimelineRepository()
    timeline_projection = TimelineProjection(timeline_repo)
    projection_manager.register_projection(timeline_projection)
    
    #   1b. Analytics Projection
    analytics_repo = AnalyticsRepository()
    analytics_projection = AnalyticsProjection(analytics_repo)
    projection_manager.register_projection(analytics_projection)
    
    #   1c. Live Stream Projection
    livestream_projection = LiveStreamProjection()
    projection_manager.register_projection(livestream_projection)
    
    # Register the single projection manager consumer
    _register(projection_manager)

    # 2. Register Operational Intelligence Engine Consumer (Priority -10)
    from app.domain.intelligence.consumer import IntelligenceEventConsumer
    intelligence_consumer = IntelligenceEventConsumer()
    _register(intelligence_consumer)
    
    # 3. Register Collaboration Engine Consumer (Priority 10)
    from app.domain.collaboration.consumer import CollaborationEventConsumer
    collaboration_consumer = CollaborationEventConsumer()
    _register(collaboration_consumer)

    # 4. Register Impact Engine Consumer (Priority 20)
    from app.domain.impact.consumer import ImpactEventConsumer
    impact_consumer = ImpactEventConsumer()
    _register(impact_consumer)

    # 5. Register Context Engine Consumer (Priority -20)
    from app.domain.context.consumer import ContextEventConsumer
    context_consumer = ContextEventConsumer()
    _register(context_consumer)

    # 6. Register Onboarding Event Consumer (Priority 100)
    from app.domain.onboarding.consumer import OnboardingEventConsumer
    onboarding_consumer = OnboardingEventConsumer()
    _register(onboarding_consumer)

    # 7. Register UI Event Consumer (Priority 1000)
    from app.domain.ui.consumer import UIEventConsumer
    ui_consumer = UIEventConsumer()
    _register(ui_consumer)

    # 8. Register Pipeline Consumers
    from app.domain.conversations.consumers.webhook_consumer import WebhookReceiveConsumer
    from app.domain.conversations.consumers.ai_consumer import AIProcessingConsumer
    from app.domain.conversations.consumers.response_consumer import ResponseConsumer
    from app.domain.integration.consumers.whatsapp_send_consumer import WhatsAppSendConsumer
    
    from app.integrations.whatsapp.config import get_whatsapp_config
    from app.integrations.whatsapp.client import WhatsAppClient
    from app.integrations.whatsapp.provider import WhatsAppProvider

    _register(WebhookReceiveConsumer())
    _register(AIProcessingConsumer())
    _register(ResponseConsumer())
    
    # Antigravity explicit dependency injection convention
    wa_config = get_whatsapp_config()
    wa_client = WhatsAppClient(config=wa_config)
    wa_provider = WhatsAppProvider(client=wa_client)
    _register(WhatsAppSendConsumer(whatsapp_provider=wa_provider))

    # 9. Register FollowUp Consumers
    from app.domain.followup.consumers.followup_consumer import FollowUpExecutedConsumer
    _register(FollowUpExecutedConsumer())

    # 10. Build DAG, Validate, and Log Execution Plans for all registered events
    validate_and_log_startup_plans(registry)


def validate_and_log_startup_plans(registry) -> dict:
    """
    Build, validate, and emit structured logs for all consumer execution plans
    across every registered event class in the registry at application startup.
    Ensures all dependencies, DAGs, and topological sort orders are valid before
    the service accepts traffic.
    """
    from app.events.worker.planner import PlanBuilder
    from app.utils.logger import get_logger

    log = get_logger(__name__)
    plans = {}

    log.info(
        "consumer_dag_startup_validation_starting",
        registered_event_types=len(registry._subscriptions),
    )

    for event_class, raw_consumers in registry._subscriptions.items():
        consumers = [
            item() if isinstance(item, type) else item
            for item in raw_consumers
        ]
        event_name = event_class.__name__
        plan = PlanBuilder.build(event_name=event_name, consumers=consumers)
        plans[event_name] = plan

    log.info(
        "consumer_dag_startup_validation_completed",
        total_event_plans=len(plans),
        total_consumers=sum(p.consumer_count for p in plans.values()),
        plans={
            name: {
                "stage_count": p.stage_count,
                "consumer_count": p.consumer_count,
                "stages": [
                    [c.__class__.__name__ for c in stage.consumers]
                    for stage in p.stages
                ],
            }
            for name, p in plans.items()
        },
    )

    return plans

