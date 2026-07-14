from app.domain.followup.schemas import QualityCheckResult

def check(message_content: str) -> QualityCheckResult:
    # Stub: check for hallucinations, bad tone, etc.
    if len(message_content) < 5:
        return QualityCheckResult(passed=False, issues=["Message too short"])
    return QualityCheckResult(passed=True, issues=[])
