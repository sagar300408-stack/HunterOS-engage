from typing import Dict, Optional

from app.domain.briefing.templates.base import BaseBriefingTemplate


class BriefingRegistry:
    """
    Registry for Executive Briefing Templates.
    """
    def __init__(self):
        self._templates: Dict[str, BaseBriefingTemplate] = {}

    def register(self, template: BaseBriefingTemplate) -> None:
        self._templates[template.template_name] = template

    def get_template(self, name: str) -> Optional[BaseBriefingTemplate]:
        return self._templates.get(name)


briefing_registry = BriefingRegistry()
