from typing import List, Dict, Any
from app.domain.impact.models import BaselineMetrics

class BenchmarkEngine:
    """
    Compares current performance against historical baselines.
    """

    @classmethod
    def calculate_improvements(cls, baselines: List[BaselineMetrics], current_metrics: Dict[str, float]) -> Dict[str, float]:
        """
        Returns a dictionary of improvement percentages.
        """
        improvements = {}
        for b in baselines:
            current = current_metrics.get(b.metric_name)
            if current is not None and b.baseline_value > 0:
                # E.g. (Baseline - Current) / Baseline
                # So if baseline was 100 mins, and current is 20 mins: (100-20)/100 = 80% improvement
                improvement_pct = ((b.baseline_value - current) / b.baseline_value) * 100
                improvements[b.metric_name] = round(improvement_pct, 2)
                
        return improvements
