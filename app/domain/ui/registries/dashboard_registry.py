from typing import Dict, Any

class DashboardRegistry:
    """
    Provides fallback/default configurations for dashboards if the database definitions are missing.
    """
    
    DEFAULT_EXECUTIVE = {
        "role": "executive",
        "widgets": [
            {"key": "business_friction", "w": 4, "h": 2, "x": 0, "y": 0},
            {"key": "roi_summary", "w": 8, "h": 2, "x": 4, "y": 0},
            {"key": "executive_narrative", "w": 12, "h": 4, "x": 0, "y": 2}
        ]
    }
    
    DEFAULT_MANAGER = {
        "role": "manager",
        "widgets": [
            {"key": "team_workload", "w": 6, "h": 3, "x": 0, "y": 0},
            {"key": "pending_approvals", "w": 6, "h": 3, "x": 6, "y": 0}
        ]
    }

    @classmethod
    def get_default(cls, role: str) -> Dict[str, Any]:
        if role == "executive":
            return cls.DEFAULT_EXECUTIVE
        if role == "manager":
            return cls.DEFAULT_MANAGER
        return {"role": role, "widgets": []}
