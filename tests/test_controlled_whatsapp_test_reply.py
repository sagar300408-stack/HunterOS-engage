import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.domain.customers.models import Customer
from app.pipeline.ai import process_with_ai

@pytest.mark.asyncio
async def test_controlled_test_reply_triggers_only_on_hi_and_authorized():
    mock_customer = MagicMock(spec=Customer)
    mock_customer.id = uuid4()
    mock_customer.phone = "919108976764"
    mock_customer.workspace_id = uuid4()
    mock_customer.created_at = None

    mock_session = AsyncMock()
    mock_exec_result = MagicMock()
    mock_exec_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_exec_result
    mock_session.scalar.return_value = None

    mock_intent = MagicMock()
    mock_intent.confidence = 0.0

    # 1. Matching case: sender is 919108976764, text is "  Hi  ", env enabled
    with patch.dict("os.environ", {
        "ENABLE_WHATSAPP_TEST_AUTO_REPLY": "true",
        "WHATSAPP_TEST_RECIPIENT_PHONE": "919108976764",
    }):
        with patch("app.pipeline.ai.get_ai_provider") as mock_get_ai:
            with patch("app.domain.conversations.service.get_conversation_history", return_value=[]):
                with patch("app.pipeline.ai.inject_memory", return_value=[]):
                    with patch("app.pipeline.ai.classify_intent", return_value=mock_intent):
                        with patch("app.domain.dashboard.service.log_pipeline_step", return_value=None):
                            with patch("app.domain.memory.service.MemoryService.get_customer_memory", return_value=None):
                                with patch("app.domain.memory.service.MemoryService.update_customer_memory", return_value=None):
                                    with patch("app.domain.customers.service.update_last_interaction", return_value=None):
                                        res = await process_with_ai(
                                            conversation_id=uuid4(),
                                            message_id=uuid4(),
                                            customer=mock_customer,
                                            user_content="  Hi  ",
                                            session=mock_session,
                                        )
                                        assert res["content"] == "THIS IS A TEST MESSAGE FROM HUNTEROS ENGAGE, BACKEND VERIFIED"
                                        mock_get_ai.assert_not_called()

    # 2. Non-matching text: "hello" from 919108976764
    with patch.dict("os.environ", {
        "ENABLE_WHATSAPP_TEST_AUTO_REPLY": "true",
        "WHATSAPP_TEST_RECIPIENT_PHONE": "919108976764",
    }):
        with patch("app.pipeline.ai.get_ai_provider") as mock_get_ai:
            mock_provider = AsyncMock()
            mock_provider.get_ai_response.return_value = {"content": "Normal AI response", "model": "gpt-4o"}
            mock_get_ai.return_value = mock_provider
            with patch("app.domain.conversations.service.get_conversation_history", return_value=[]):
                with patch("app.pipeline.ai.inject_memory", return_value=[]):
                    with patch("app.pipeline.ai.classify_intent", return_value=mock_intent):
                        with patch("app.domain.dashboard.service.log_pipeline_step", return_value=None):
                            with patch("app.domain.memory.service.MemoryService.get_customer_memory", return_value=None):
                                with patch("app.domain.memory.service.MemoryService.update_customer_memory", return_value=None):
                                    with patch("app.domain.customers.service.update_last_interaction", return_value=None):
                                        res = await process_with_ai(
                                            conversation_id=uuid4(),
                                            message_id=uuid4(),
                                            customer=mock_customer,
                                            user_content="hello",
                                            session=mock_session,
                                        )
                                        assert res["content"] == "Normal AI response"
                                        mock_provider.get_ai_response.assert_called_once()

    # 3. Non-matching recipient: text is "hi" from different phone
    unauthorized_customer = MagicMock(spec=Customer)
    unauthorized_customer.id = uuid4()
    unauthorized_customer.phone = "1234567890"
    unauthorized_customer.workspace_id = uuid4()
    unauthorized_customer.created_at = None

    with patch.dict("os.environ", {
        "ENABLE_WHATSAPP_TEST_AUTO_REPLY": "true",
        "WHATSAPP_TEST_RECIPIENT_PHONE": "919108976764",
    }):
        with patch("app.pipeline.ai.get_ai_provider") as mock_get_ai:
            mock_provider = AsyncMock()
            mock_provider.get_ai_response.return_value = {"content": "Normal AI response", "model": "gpt-4o"}
            mock_get_ai.return_value = mock_provider
            with patch("app.domain.conversations.service.get_conversation_history", return_value=[]):
                with patch("app.pipeline.ai.inject_memory", return_value=[]):
                    with patch("app.pipeline.ai.classify_intent", return_value=mock_intent):
                        with patch("app.domain.dashboard.service.log_pipeline_step", return_value=None):
                            with patch("app.domain.memory.service.MemoryService.get_customer_memory", return_value=None):
                                with patch("app.domain.memory.service.MemoryService.update_customer_memory", return_value=None):
                                    with patch("app.domain.customers.service.update_last_interaction", return_value=None):
                                        res = await process_with_ai(
                                            conversation_id=uuid4(),
                                            message_id=uuid4(),
                                            customer=unauthorized_customer,
                                            user_content="hi",
                                            session=mock_session,
                                        )
                                        assert res["content"] == "Normal AI response"
                                        mock_provider.get_ai_response.assert_called_once()

    # 4. Gated/Disabled: ENABLE_WHATSAPP_TEST_AUTO_REPLY="false"
    with patch.dict("os.environ", {
        "ENABLE_WHATSAPP_TEST_AUTO_REPLY": "false",
        "WHATSAPP_TEST_AUTO_REPLY": "false",
        "WHATSAPP_TEST_RECIPIENT_PHONE": "919108976764",
    }):
        with patch("app.pipeline.ai.get_ai_provider") as mock_get_ai:
            mock_provider = AsyncMock()
            mock_provider.get_ai_response.return_value = {"content": "Normal AI response", "model": "gpt-4o"}
            mock_get_ai.return_value = mock_provider
            with patch("app.domain.conversations.service.get_conversation_history", return_value=[]):
                with patch("app.pipeline.ai.inject_memory", return_value=[]):
                    with patch("app.pipeline.ai.classify_intent", return_value=mock_intent):
                        with patch("app.domain.dashboard.service.log_pipeline_step", return_value=None):
                            with patch("app.domain.memory.service.MemoryService.get_customer_memory", return_value=None):
                                with patch("app.domain.memory.service.MemoryService.update_customer_memory", return_value=None):
                                    with patch("app.domain.customers.service.update_last_interaction", return_value=None):
                                        res = await process_with_ai(
                                            conversation_id=uuid4(),
                                            message_id=uuid4(),
                                            customer=mock_customer,
                                            user_content="hi",
                                            session=mock_session,
                                        )
                                        assert res["content"] == "Normal AI response"
                                        mock_provider.get_ai_response.assert_called_once()

    # 5. Already processed: event already exists in EventRecord
    mock_already_processed_result = MagicMock()
    mock_already_processed_result.scalar_one_or_none.return_value = uuid4()
    mock_session_already_processed = AsyncMock()
    mock_session_already_processed.execute.return_value = mock_already_processed_result
    mock_session_already_processed.scalar.return_value = None

    with patch.dict("os.environ", {
        "ENABLE_WHATSAPP_TEST_AUTO_REPLY": "true",
        "WHATSAPP_TEST_RECIPIENT_PHONE": "919108976764",
    }):
        with patch("app.pipeline.ai.get_ai_provider") as mock_get_ai:
            mock_provider = AsyncMock()
            mock_provider.get_ai_response.return_value = {"content": "Normal AI response", "model": "gpt-4o"}
            mock_get_ai.return_value = mock_provider
            with patch("app.domain.conversations.service.get_conversation_history", return_value=[]):
                with patch("app.pipeline.ai.inject_memory", return_value=[]):
                    with patch("app.pipeline.ai.classify_intent", return_value=mock_intent):
                        with patch("app.domain.dashboard.service.log_pipeline_step", return_value=None):
                            with patch("app.domain.memory.service.MemoryService.get_customer_memory", return_value=None):
                                with patch("app.domain.memory.service.MemoryService.update_customer_memory", return_value=None):
                                    with patch("app.domain.customers.service.update_last_interaction", return_value=None):
                                        res = await process_with_ai(
                                            conversation_id=uuid4(),
                                            message_id=uuid4(),
                                            customer=mock_customer,
                                            user_content="hi",
                                            session=mock_session_already_processed,
                                        )
                                        assert res["content"] == "Normal AI response"
                                        mock_provider.get_ai_response.assert_called_once()
