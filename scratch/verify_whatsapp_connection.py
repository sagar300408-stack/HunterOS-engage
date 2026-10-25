import asyncio
from app.integrations.whatsapp.config import get_whatsapp_config
from app.integrations.whatsapp.client import WhatsAppClient
from app.integrations.whatsapp.provider import WhatsAppProvider

async def main():
    wa_config = get_whatsapp_config()
    client = WhatsAppClient(config=wa_config)
    provider = WhatsAppProvider(client=client)
    res = await provider.verify_connection()
    print(f"WHATSAPP_CREDENTIALS_VALID: {res}")

if __name__ == "__main__":
    asyncio.run(main())
