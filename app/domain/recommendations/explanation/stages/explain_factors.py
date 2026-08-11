from typing import Any, Dict, List
from ..rules.registry import RecommendationExplanationRuleRegistry
from ..rules.base import ExplanationSection

def explain_factors(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 4: Executes registered factor explanation rules. NO score recalculation.
    """
    sections: List[ExplanationSection] = []
    
    rules = RecommendationExplanationRuleRegistry.get_all_rules()
    for rule in rules:
        section = rule.explain(data)
        if section:
            sections.append(section)
            
    data['explanation_sections'] = sections
    return data
