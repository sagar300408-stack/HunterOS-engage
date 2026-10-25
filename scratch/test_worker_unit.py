import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.getcwd())

async def test_worker_execution():
    from app.domain.followup.models import FollowUpQueue
    from app.domain.customers.models import Customer
    from app.worker.followup_worker import process_due_followups

    fu_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    mock_fu = FollowUpQueue(
        id=fu_id,
        customer_id=cust_id,
        conversation_id=conv_id,
        workspace_id=ws_id,
        status="scheduled",
        scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=5),
        human_paused=False,
        priority=1,
        generated_message="Hello, following up regarding your inquiry",
        retry_count=0
    )

    mock_cust = Customer(
        id=cust_id,
        workspace_id=ws_id,
        phone="+1234567890",
    )

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.return_value = mock_fu
    mock_session.execute.return_value = mock_res
    mock_session.get.side_effect = lambda model, oid: mock_fu if oid == fu_id else mock_cust

    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None

    with (
        patch("app.worker.followup_worker.get_session", return_value=mock_session_ctx),
        patch("app.worker.followup_worker.EventBus.publish", new=AsyncMock()),
    ):
        processed = await process_due_followups()
        assert processed is True, "process_due_followups should return True when an item is processed"
        assert mock_fu.status == "sent", f"FollowUp status should be 'sent', got {mock_fu.status}"
        assert mock_fu.retry_count == 1, f"retry_count should be incremented to 1, got {mock_fu.retry_count}"
        print("[WORKER EXEC TEST] process_due_followups executed cleanly and transitioned status to 'sent'!")

if __name__ == "__main__":
    asyncio.run(test_worker_execution())
