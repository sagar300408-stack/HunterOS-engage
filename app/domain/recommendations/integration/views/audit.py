from .base import BaseRecommendationView
from typing import List, Dict, Any, Optional

class AuditView(BaseRecommendationView):
    """
    DTO model for audit projection.
    """
    audit_trail: List[Dict[str, Any]] = []
    compliance_flags: List[str] = []
    reviewed_by: Optional[str] = None
