from typing import List, Dict, Any

class DataQualityEngine:
    """
    Evaluates imported data for duplicates and missing required fields.
    """

    @classmethod
    def evaluate_batch(cls, entity_type: str, records: List[Dict[str, Any]]) -> float:
        """
        Returns a quality score between 0.0 and 1.0.
        """
        if not records:
            return 1.0
            
        issues = 0
        seen_ids = set()
        
        for record in records:
            ext_id = record.get("external_id")
            
            if ext_id in seen_ids:
                issues += 1 # Duplicate
            else:
                seen_ids.add(ext_id)
                
            if entity_type == "CUSTOMER":
                if not record.get("email"):
                    issues += 1
                if not record.get("phone"):
                    issues += 1
                    
        # Score calculation: 1.0 minus penalty for issues
        penalty = (issues / (len(records) * 2)) # Assume 2 required checks per record
        score = max(0.0, 1.0 - penalty)
        
        return round(score, 2)
