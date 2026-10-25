import sys, os
sys.path.insert(0, os.getcwd())

from app.config import get_settings
settings = get_settings()

print(f"[WHATSAPP CONFIG] Phone Number ID present: {bool(settings.whatsapp_phone_number_id)}")
print(f"[WHATSAPP CONFIG] Access Token present: {bool(settings.whatsapp_access_token)}")
print(f"[WHATSAPP CONFIG] Verify Token present: {bool(settings.whatsapp_verify_token)}")
print(f"[WHATSAPP CONFIG] API Version: {settings.whatsapp_api_version}")

is_mock_token = (
    not settings.whatsapp_access_token
    or settings.whatsapp_access_token.startswith("mock-")
    or settings.whatsapp_access_token in ("test_access_token", "your-access-token", "placeholder")
    or len(settings.whatsapp_access_token) < 20
)
is_mock_phone = (
    not settings.whatsapp_phone_number_id
    or settings.whatsapp_phone_number_id in ("123456789", "your-phone-id", "000000000")
)

print(f"[WHATSAPP CONFIG] Token appears to be mock/test: {is_mock_token}")
print(f"[WHATSAPP CONFIG] Phone ID appears to be mock/test: {is_mock_phone}")
