# Live WhatsApp Round-Trip Test Report: HunterOS Engage

## Executive Summary
- **Overall Result**: **READY FOR LIVE INITIATION (PREFLIGHT PASSED)**
- **Objective**: Execute a controlled WhatsApp round-trip verification where the authorized test recipient sends `hi` and HunterOS Engage responds with:
  ```text
  TEST SUCCESSFULL, THIS WAS A TEST MESSAGE FROM HUNTEROS ENGAGE
  ```
- **Change Control**: All architecture invariants preserved. No bypass of transactional outbox, Celery, or consumer pipeline. Narrowly gated test auto-reply active only for authorized recipient (`+91...764`) and message `hi`.

---

## 1. Preflight Verification Matrix

| Check Item | Requirement | Verification Method | Result | Evidence / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **1. Public Inbound Route** | Route Meta webhooks to app port/path | Cloudflare tunnel verification + GET handshake probe | **PASS** | `https://webhook.originyx.in/api/v1/webhook` -> `localhost:8000`. GET challenge verified (HTTP 200). |
| **2. Signature Verification** | Meta `X-Hub-Signature-256` validation | Synthetic probe with invalid and valid HMAC-SHA256 signatures | **PASS** | Invalid signature rejected with HTTP 403; valid signature accepted with HTTP 200. |
| **3. Webhook Subscription** | Subscribed to incoming WhatsApp messages | Meta Graph API query (`/v20.0/2165694718159803/subscribed_apps`) | **PASS** | App `HunterOS Engage TEST` (ID `1569919341541930`) subscribed to WABA. |
| **4. WhatsApp Business Account** | Correct WABA & phone configuration | Meta Graph API query (`/v20.0/1260054017187362`) | **PASS** | Phone ID `1260054017187362` (+1 555-674-4757), `verified_name: Test Number`, Quality `GREEN`. |
| **5. Inbound Persistence** | Inbound messages saved to DB via outbox | Outbox event model inspection | **PASS** | Webhook maps to `RawWebhookEvent` -> `event_store` -> `WebhookReceiveConsumer` -> `Message` table. |
| **6. Database & Broker** | PostgreSQL & Redis reachable | Connection probes | **PASS** | Postgres 15 (port 5432) and Redis 7 (port 6379) healthy. |
| **7. Worker & Dispatcher** | Running current code | Container runtime & DAG log inspection | **PASS** | Containers restarted with mounted code. DAG validated for `RawWebhookEvent`, `MessageReceived`, `AIResponded`, `MessageReadyToSendEvent`. |
| **8. Queue Isolation** | No competing or stale workers | Process inspection & socket binding audit | **PASS** | Stale host uvicorn/worker processes terminated. Single active Celery worker on queues `event_dispatch,celery`. |
| **9. Recipient Resolution** | Recipient mapped to customer & workspace | Database customer & workspace check | **PASS** | Recipient `+91...764` mapped to Customer `bbe8aa52-068d-4bce-a071-4aec7e7e2cbb`, Workspace `00000000-0000-0000-0000-000000000001`. |
| **10. Pending Backlog** | No pending test events in outbox/queues | Event store query | **PASS** | 0 pending `MessageReadyToSendEvent` or `MessageReceived` records. Queue length 0. |

---

## 2. Controlled Test-Only Implementation

### Controlled Trigger Gate (`app/pipeline/ai.py`)
```python
test_mode_enabled = (
    os.environ.get("ENABLE_WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true"
    or os.environ.get("WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true"
)
authorized_recipient = normalize_phone(os.environ.get("WHATSAPP_TEST_RECIPIENT_PHONE", "919108976764"))
sender_phone = normalize_phone(customer.phone) if customer and customer.phone else ""
is_authorized_recipient = bool(sender_phone and sender_phone == authorized_recipient)
is_hi_message = bool(user_content and user_content.strip().lower() == "hi")
```

### Exact Response String
```text
TEST SUCCESSFULL, THIS WAS A TEST MESSAGE FROM HUNTEROS ENGAGE
```

- **Scope**: Narrowly gated to `+91...764` sending `hi`.
- **Fallthrough**: Any other message or customer falls through to standard OpenAI conversational provider.
- **Idempotency**: Checked against existing events in `event_store` to prevent re-generation on message retries.
- **Disabling**: Set `ENABLE_WHATSAPP_TEST_AUTO_REPLY=false` and `WHATSAPP_TEST_AUTO_REPLY=false`.

---

## 3. Live Round-Trip Execution Evidence
*(Awaiting recipient initiation: sender must send `hi` to the configured WhatsApp number)*

- **Inbound Webhook Delivery**: Pending
- **Inbound Message ID (`wa_message_id`)**: Pending
- **Correlation ID**: Pending
- **Customer & Workspace Resolution**: Verified in Preflight (`bbe8aa52...` / `00000000...`)
- **Outbox Persistence (`RawWebhookEvent` -> `MessageReceived` -> `AIResponded` -> `MessageReadyToSendEvent`)**: Pending
- **Celery Execution**: Pending
- **WhatsApp Provider Submission (`wa_message_id`)**: Pending
- **Meta Delivery Status Webhook**: Pending
- **Duplicate Prevention Verification**: Pending

---

## 4. Instructions for Authorized Recipient
1. Send the WhatsApp message:
   ```text
   hi
   ```
   to our configured WhatsApp Business Number: **`+1 555-674-4757`** (or **`+91 63632 66193`**).
2. The background monitor (`task-393`) is actively tracking the database and event store and will record each pipeline transition.
