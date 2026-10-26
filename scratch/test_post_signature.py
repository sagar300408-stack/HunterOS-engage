import urllib.request
import urllib.error
import hmac
import hashlib
from app.config import get_settings

s = get_settings()

url = "https://webhook.originyx.in/api/v1/webhook"
body = b'{"object": "whatsapp_business_account", "entry": []}'

# 1. Test invalid signature -> must return 403
req_invalid = urllib.request.Request(
    url,
    data=body,
    headers={
        "User-Agent": "facebookplatform/1.0 (+http://developers.facebook.com)",
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=invalid_signature_hex_1234567890abcdef",
    }
)
try:
    urllib.request.urlopen(req_invalid)
    print("INVALID SIG TEST: FAILED (Expected 403, got 200)")
except urllib.error.HTTPError as e:
    print(f"INVALID SIG TEST: PASSED (Returned {e.code})")

# 2. Test valid signature -> must return 200
valid_sig = "sha256=" + hmac.new(s.whatsapp_access_token.encode("utf-8"), body, hashlib.sha256).hexdigest()
req_valid = urllib.request.Request(
    url,
    data=body,
    headers={
        "User-Agent": "facebookplatform/1.0 (+http://developers.facebook.com)",
        "Content-Type": "application/json",
        "X-Hub-Signature-256": valid_sig,
    }
)
try:
    resp = urllib.request.urlopen(req_valid)
    print(f"VALID SIG TEST: PASSED (Returned {resp.status} {resp.read().decode()})")
except urllib.error.HTTPError as e:
    print(f"VALID SIG TEST: FAILED (Returned {e.code}: {e.read().decode()})")
