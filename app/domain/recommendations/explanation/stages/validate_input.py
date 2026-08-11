from typing import Any, Dict

def validate_input(data: Dict[str, Any], workspace_id: str, identity_id: str) -> Dict[str, Any]:
    """
    Stage 2: Validates inputs are strictly matching workspace and identity.
    """
    if data.get('workspace_id') != workspace_id:
        raise ValueError(f"Workspace mismatch: expected {workspace_id}, got {data.get('workspace_id')}")
    if data.get('identity_id') != identity_id:
        raise ValueError(f"Identity mismatch: expected {identity_id}, got {data.get('identity_id')}")
    
    return data
