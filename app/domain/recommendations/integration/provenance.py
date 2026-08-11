from typing import List, Any
from datetime import datetime
from .models import ContextProvenance

def extract_lineage_metadata(lineage_id: str, upstream_assemblies: List[Any]) -> ContextProvenance:
    upstream_ids = []
    for assembly in upstream_assemblies:
        if hasattr(assembly, 'artifact_id'):
            upstream_ids.append(assembly.artifact_id)
        elif hasattr(assembly, 'id'):
            upstream_ids.append(assembly.id)
            
    return ContextProvenance(
        lineage_id=lineage_id,
        upstream_ids=upstream_ids,
        assembly_timestamp=datetime.utcnow()
    )
