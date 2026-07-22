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
    registry.register(projection_manager)

    # 2. Register Operational Intelligence Engine Consumer (Priority -10)
    from app.domain.intelligence.consumer import IntelligenceEventConsumer
    intelligence_consumer = IntelligenceEventConsumer()
    registry.register(intelligence_consumer)
    
    # 3. Register Collaboration Engine Consumer (Priority 10)
    from app.domain.collaboration.consumer import CollaborationEventConsumer
    collaboration_consumer = CollaborationEventConsumer()
    registry.register(collaboration_consumer)

    # 4. Register Impact Engine Consumer (Priority 20)
    from app.domain.impact.consumer import ImpactEventConsumer
    impact_consumer = ImpactEventConsumer()
    registry.register(impact_consumer)

    # 5. Register Context Engine Consumer (Priority -20)
    from app.domain.context.consumer import ContextEventConsumer
    context_consumer = ContextEventConsumer()
    registry.register(context_consumer)

    # 6. Register Onboarding Event Consumer (Priority 100)
    from app.domain.onboarding.consumer import OnboardingEventConsumer
    onboarding_consumer = OnboardingEventConsumer()
    registry.register(onboarding_consumer)

    # 7. Register UI Event Consumer (Priority 1000)
    from app.domain.ui.consumer import UIEventConsumer
    ui_consumer = UIEventConsumer()
    registry.register(ui_consumer)

    # 8. Register Pipeline Consumers
    from app.domain.conversations.consumers.webhook_consumer import WebhookReceiveConsumer
    from app.domain.conversations.consumers.ai_consumer import AIProcessingConsumer
    from app.domain.conversations.consumers.response_consumer import ResponseConsumer
    from app.domain.integration.consumers.whatsapp_send_consumer import WhatsAppSendConsumer

    registry.register(WebhookReceiveConsumer())
    registry.register(AIProcessingConsumer())
    registry.register(ResponseConsumer())
    registry.register(WhatsAppSendConsumer())

    # 9. Register FollowUp Consumers
    from app.domain.followup.consumers.followup_consumer import FollowUpExecutedConsumer
    registry.register(FollowUpExecutedConsumer())

