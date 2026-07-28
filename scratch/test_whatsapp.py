import asyncio
from app.integrations.whatsapp.config import get_whatsapp_config
from app.integrations.whatsapp.client import WhatsAppClient
from app.integrations.whatsapp.provider import WhatsAppProvider

async def main():
    try:
        # Resolve dependencies (Antigravity pattern)
        config = get_whatsapp_config()
        client = WhatsAppClient(config)
        provider = WhatsAppProvider(client)
        
        # Test 1: Verify Connection
        print("Verifying connection...")
        verified = await provider.verify_connection()
        print(f"Verified: {verified}")
        
        # Test 2: Send Test Message
        if verified:
            print("Sending test message...")
            response = await provider.send_test_message("+919108976764")
            print(f"Response: {response}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
