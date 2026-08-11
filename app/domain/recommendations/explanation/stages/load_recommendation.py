from typing import Any, Dict

def load_recommendation(recommendation_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 1: Loads the candidate, prioritized recommendation, and evidence.
    """
    # In a real implementation, this would fetch from a database or service.
    # Here, we assume context already contains the loaded data for simplicity,
    # or we simulate loading.
    loaded_data = context.get('initial_data', {})
    loaded_data['recommendation_id'] = recommendation_id
    return loaded_data
