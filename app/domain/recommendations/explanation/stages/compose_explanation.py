from typing import Any, Dict
from ..rules.base import ExplanationSection

def compose_explanation(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 5: Composes sections and builds deterministic templated strings.
    Adds limitations for missing evidence.
    """
    sections = data.get('explanation_sections', [])
    
    reason_parts = []
    for section in sections:
        reason_parts.append(f"{section.title}: {section.content}")
        
    if not data.get('evidence'):
        reason_parts.append("Limitation: No concrete evidence was provided for this recommendation.")
        
    data['composed_reason'] = "\\n".join(reason_parts)
    data['composed_summary'] = f"Recommendation based on {len(sections)} factors."
    
    return data
