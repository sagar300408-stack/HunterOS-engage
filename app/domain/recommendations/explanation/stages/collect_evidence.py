from typing import Any, Dict, List

def collect_evidence(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 3: Calls EvidenceCollector to normalize evidence into ExplanationEvidence references.
    """
    raw_evidence = data.get('raw_evidence', [])
    normalized_evidence = []
    
    for i, item in enumerate(raw_evidence):
        normalized_evidence.append({
            'id': f"ev_{i}",
            'description': str(item)
        })
        
    data['evidence'] = normalized_evidence
    return data
