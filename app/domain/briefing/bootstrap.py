from app.domain.briefing.templates.registry import briefing_registry
from app.domain.briefing.templates.standard_templates import CEODailyBriefing, SalesManagerBriefing


def bootstrap_briefings():
    """
    Registers all standard Executive Briefing templates in the global registry.
    """
    briefing_registry.register(CEODailyBriefing())
    briefing_registry.register(SalesManagerBriefing())
