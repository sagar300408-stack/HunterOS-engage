import httpx
from typing import Dict, Any, List

class HunterOSClient:
    """
    Official Python SDK for interacting with HunterOS Engage.
    """
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.Client(headers=self.headers, base_url=self.base_url)

    def publish_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publishes a custom event to the HunterOS Event Bus.
        """
        data = {
            "event_type": event_type,
            "payload": payload
        }
        # Assuming there's a generic events ingest endpoint
        response = self.client.post("/api/v1/events", json=data)
        response.raise_for_status()
        return response.json()
        
    def get_friction_score(self, workspace_id: str) -> float:
        """
        Retrieves the current Business Friction Score for the workspace.
        """
        response = self.client.get(f"/api/v1/friction/{workspace_id}/score")
        response.raise_for_status()
        return response.json().get("score", 0.0)

    def close(self):
        self.client.close()
