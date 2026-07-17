import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.domain.marketplace.models import ConnectorDefinition, ConnectorCategory, ConnectorCertification, ConnectorType, ConnectorStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MOCK_CONNECTORS = [
    {
        "connector_id": "mock_crm_v1",
        "name": "Mock CRM Connector",
        "description": "A certified mock CRM connector for testing.",
        "vendor": "HunterOS",
        "category": ConnectorCategory.CRM.value,
        "certification": ConnectorCertification.CERTIFIED.value,
        "connector_type": ConnectorType.NATIVE.value,
        "status": ConnectorStatus.ACTIVE.value,
        "version": "1.0.0",
        "supported_platform_versions": ">=1.0.0",
        "supported_capabilities": ["CREATE_CONTACT", "READ_CONTACT", "UPDATE_CONTACT", "DELETE_CONTACT"],
        "required_credentials": {
            "type": "object",
            "properties": {
                "api_key": {"type": "string"}
            },
            "required": ["api_key"]
        },
        "configuration_schema": {
            "type": "object",
            "properties": {
                "base_url": {"type": "string", "default": "https://api.mockcrm.example.com"}
            }
        }
    },
    {
        "connector_id": "mock_slack_v1",
        "name": "Mock Slack Connector",
        "description": "A community mock Slack connector.",
        "vendor": "HunterOS Community",
        "category": ConnectorCategory.COMMUNICATION.value,
        "certification": ConnectorCertification.COMMUNITY.value,
        "connector_type": ConnectorType.EXTERNAL.value,
        "status": ConnectorStatus.ACTIVE.value,
        "version": "1.1.0",
        "supported_platform_versions": ">=1.0.0",
        "supported_capabilities": ["SEND_MESSAGE", "CREATE_CHANNEL"],
        "required_credentials": {
            "type": "object",
            "properties": {
                "bot_token": {"type": "string"}
            },
            "required": ["bot_token"]
        },
        "configuration_schema": {
            "type": "object",
            "properties": {
                "default_channel": {"type": "string"}
            }
        }
    },
    {
        "connector_id": "mock_email_v1",
        "name": "Mock Email Connector",
        "description": "Send emails through mock SMTP.",
        "vendor": "HunterOS",
        "category": ConnectorCategory.EMAIL.value,
        "certification": ConnectorCertification.CERTIFIED.value,
        "connector_type": ConnectorType.NATIVE.value,
        "status": ConnectorStatus.ACTIVE.value,
        "version": "2.0.0",
        "supported_platform_versions": ">=1.1.0",
        "supported_capabilities": ["SEND_EMAIL"],
        "required_credentials": {},
        "configuration_schema": {
            "type": "object",
            "properties": {
                "smtp_host": {"type": "string"}
            }
        }
    }
]

async def seed_marketplace():
    async with async_session_maker() as session:
        for mock_data in MOCK_CONNECTORS:
            stmt = select(ConnectorDefinition).where(ConnectorDefinition.connector_id == mock_data["connector_id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                definition = ConnectorDefinition(**mock_data)
                session.add(definition)
                logger.info(f"Seeding new connector: {mock_data['connector_id']} v{mock_data['version']}")
            else:
                for k, v in mock_data.items():
                    setattr(existing, k, v)
                logger.info(f"Updated existing connector: {mock_data['connector_id']} v{mock_data['version']}")
                
        await session.commit()
        logger.info("Marketplace seed complete.")

if __name__ == "__main__":
    asyncio.run(seed_marketplace())
