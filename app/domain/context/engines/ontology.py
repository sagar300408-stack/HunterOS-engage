from typing import Dict
import uuid

from app.domain.context.repository import ContextRepository

class BusinessOntologyEngine:
    """
    Translates internal canonical concepts to company-specific terminology for UI/display.
    The backend stays canonical; this engine maps outward.
    """

    @classmethod
    async def get_mapping(cls, repo: ContextRepository, workspace_id: uuid.UUID) -> Dict[str, str]:
        """
        Returns a dictionary mapping internal -> display.
        Example: {"CUSTOMER": "Client", "PROJECT": "Job"}
        """
        return await repo.get_ontology_map(workspace_id)

    @classmethod
    def apply_to_payload(cls, payload: Dict[str, str], mapping: Dict[str, str]) -> Dict[str, str]:
        """
        Translates string values or keys for UI consumption.
        In a real app, this would deeply traverse dicts/lists.
        """
        # Shallow translation example
        translated = {}
        for k, v in payload.items():
            # Translate keys
            new_k = mapping.get(k.upper(), k)
            
            # Translate values if string
            new_v = v
            if isinstance(v, str):
                new_v = mapping.get(v.upper(), v)
                
            translated[new_k] = new_v
            
        return translated
