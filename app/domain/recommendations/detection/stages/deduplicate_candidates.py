import hashlib
from typing import Any, List

class DeduplicateCandidatesStage:
    def execute(self, candidates: List[Any], diagnostics: Any) -> List[Any]:
        """
        Generates a deterministic candidate fingerprint using SHA256 of:
        workspace_id + target_id + recommendation_type + trigger_type + sorted(evidence_ids) + rule_id + rule_version.
        For duplicates matching this fingerprint, merges evidence references deterministically.
        Does NOT save to DB. Updates deduplicated count in diagnostics.
        
        Args:
            candidates: List of validated RecommendationCandidate objects
            diagnostics: DetectionDiagnostics instance
            
        Returns:
            List[RecommendationCandidate]: Deduplicated candidates
        """
        deduplicated = {}
        original_count = len(candidates)
        
        for candidate in candidates:
            fingerprint = self._generate_fingerprint(candidate)
            
            if fingerprint in deduplicated:
                existing = deduplicated[fingerprint]
                self._merge_evidence(existing, candidate)
            else:
                deduplicated[fingerprint] = candidate
                
        deduped_list = list(deduplicated.values())
        
        if hasattr(diagnostics, "candidates_deduplicated"):
            # The count of candidates that were removed as duplicates
            diagnostics.candidates_deduplicated += (original_count - len(deduped_list))
            
        return deduped_list

    def _generate_fingerprint(self, candidate: Any) -> str:
        """
        Creates a deterministic fingerprint for deduplication.
        """
        evidence_ids = getattr(candidate, 'evidence_ids', [])
        sorted_evidence = sorted([str(eid) for eid in evidence_ids])
        
        parts = [
            str(getattr(candidate, 'workspace_id', '')),
            str(getattr(candidate, 'target_id', '')),
            str(getattr(candidate, 'recommendation_type', '')),
            str(getattr(candidate, 'trigger_type', '')),
            "|".join(sorted_evidence),
            str(getattr(candidate, 'rule_id', '')),
            str(getattr(candidate, 'rule_version', ''))
        ]
        
        concat_str = "::".join(parts)
        return hashlib.sha256(concat_str.encode('utf-8')).hexdigest()

    def _merge_evidence(self, target: Any, source: Any) -> None:
        """
        Deterministically merges evidence references from source into target.
        """
        target_evidence = set(getattr(target, 'evidence_ids', []))
        source_evidence = set(getattr(source, 'evidence_ids', []))
        
        merged_evidence = sorted(list(target_evidence | source_evidence))
        
        if hasattr(target, 'evidence_ids'):
            target.evidence_ids = merged_evidence
