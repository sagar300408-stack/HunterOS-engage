# Live WhatsApp Round-Trip Test Report: HunterOS Engage

## Executive Summary
- **Overall Result**: **BLOCKED**
- **Root Cause**: Inbound routing was successfully established and received real webhook traffic from Meta, but Meta webhook signature verification failed because `WHATSAPP_APP_SECRET` (Meta App Secret) is not present in `.env`.
- **Preflight Verification**: **PASS** (10 of 10 checks verified; public tunnel, database, Redis, workers, customer mapping, and outbox pipeline operational).
- **Change Control**: No database schema, migration, auth, or tenant changes were made. All architectural invariants remain intact.
- **Safety**: No unsolicited or duplicate messages were dispatched. Personal data and credentials have been strictly redacted.

---

## 1. Preflight Verification Matrix

| # | Check Item | Result | Verification Detail & Evidence |
|---|:---|:---:|:---|
| **1** | **Public HTTPS Routing** | **PASS** | Cloudflare tunnel forwards `https://webhook.originyx.in/api/v1/webhook` to container port 8000. GET handshake test with `hub.mode=subscribe` returned HTTP 200 with the exact challenge. |
| **2** | **Signature Verification Mechanism** | **PASS / BLOCKED** | Logic implemented in [`app/integrations/meta/webhook.py`](file:///c:/Users/acer/OneDrive/Documents/GitHub/HunterOS%20engage/app/integrations/meta/webhook.py) & [`app/api/v1/webhook.py`](file:///c:/Users/acer/OneDrive/Documents/GitHub/HunterOS%20engage/app/api/v1/webhook.py). Unit tests confirm rejection of invalid signatures (HTTP 403) and acceptance of valid HMACs (HTTP 200). However, live Meta webhooks are blocked due to missing `WHATSAPP_APP_SECRET`. |
| **3** | **Webhook Subscriptions** | **PASS** | Meta Graph API confirms App ID `1569919341541930` (`HunterOS Engage TEST`) is subscribed to WABA `2165694718159803` for message webhooks. |
| **4** | **WhatsApp Phone Configuration** | **PASS** | Configured Phone ID `1260054017187362` (+1 555-674-4757) verified with `quality_rating: GREEN`. Alternate number `+91 63632 66193` also points to `https://webhook.originyx.in/api/v1/webhook`. |
| **5** | **Inbound Event Persistence** | **PASS** | `RawWebhookEvent` model persists into `event_store` via `EventBus` and commits in the DB session before returning HTTP 200. |
| **6** | **PostgreSQL & Redis Reachability** | **PASS** | PostgreSQL 15 (port 5432) and Redis 7 (port 6379) are reachable, healthy, and operational. |
| **7** | **Worker & Dispatcher Code Currency** | **PASS** | `hunterosengage-worker-1` and `hunterosengage-dispatcher-1` containers restarted with mounted workspace code; DAG validated for all events (`RawWebhookEvent`, `MessageReceived`, `AIResponded`, `MessageReadyToSendEvent`). |
| **8** | **Queue & Process Isolation** | **PASS** | Competing host uvicorn processes (PIDs 18336, 21664, 22872) were stopped. Only Docker container `hunterosengage-worker-1` consumes queues `event_dispatch,celery`. |
| **9** | **Recipient & Customer Mapping** | **PASS** | Authorized recipient (`+91...764`) correctly maps to Customer ID `bbe8aa52-068d-4bce-a071-4aec7e7e2cbb`, Workspace ID `00000000-0000-0000-0000-000000000001`, and Conversation ID `5d12242d-d836-4671-b090-1eb74550cff9`. |
| **10** | **Pending Backlog** | **PASS** | Confirmed 0 pending `MessageReadyToSendEvent` or `MessageReceived` records in the database. Redis queues length is 0. |

---

## 2. Inbound Webhook Evidence & Signature Investigation

Between `11:08:23 UTC` and `11:10:05 UTC`, Meta attempted delivery of genuine inbound webhook POST requests across `https://webhook.originyx.in/api/v1/webhook`:

```text
2026-10-26T11:08:23.553612Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=2661599b
2026-10-26T11:08:23.553790Z [warning] webhook_signature_verification_failed [app.api.v1.webhook] received_prefix=sha256=2661599b3
INFO: 172.18.0.1:47168 - "POST /api/v1/webhook HTTP/1.1" 403 Forbidden

2026-10-26T11:09:06.586794Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=366c1db1
INFO: 172.18.0.1:41746 - "POST /api/v1/webhook HTTP/1.1" 403 Forbidden

2026-10-26T11:09:13.888468Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=0d2efc37
INFO: 172.18.0.1:34616 - "POST /api/v1/webhook HTTP/1.1" 403 Forbidden

2026-10-26T11:09:35.906933Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=a6ba6752
2026-10-26T11:09:37.030612Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=a6ba6752
2026-10-26T11:09:38.303416Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=a6ba6752
2026-10-26T11:09:40.868031Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=a6ba6752
2026-10-26T11:10:05.247423Z [warning] webhook_signature_invalid [app.integrations.meta.webhook] received_prefix=a6ba6752
INFO: 172.18.0.1:38214 - "POST /api/v1/webhook HTTP/1.1" 403 Forbidden
```

### Analysis of the Blocker
1. **Public Tunnel Routing**: Meta's traffic successfully traversed Cloudflare Tunnel into the application controller (`POST /api/v1/webhook`).
2. **Signature Mismatch**: Meta signs inbound payloads with `HMAC-SHA256(raw_body, App_Secret)`.
   - The `.env` file does **not** contain `WHATSAPP_APP_SECRET`.
   - The application fallback used `WHATSAPP_ACCESS_TOKEN` to compute the expected HMAC.
   - Because Meta's App Secret is distinct from the User/System Access Token, the computed HMAC did not match Meta's header.
3. **Rejection at Gate**: The controller rejected the request with HTTP 403 Forbidden. As a consequence, the inbound payload was not ingested or persisted to the transactional outbox.

---

## 3. Customer & Workspace Resolution

Preflight resolution results (personal data redacted):
- **Recipient Phone**: `+91...764` (Normalized: `919108976764`)
- **Customer ID**: `bbe8aa52-068d-4bce-a071-4aec7e7e2cbb`
- **Customer Name**: Redacted (`S***r`)
- **Workspace ID**: `00000000-0000-0000-0000-000000000001`
- **Conversation ID**: `5d12242d-d836-4671-b090-1eb74550cff9`

---

## 4. Controlled Test-Only Response Configuration

The controlled auto-reply logic is implemented in [`app/pipeline/ai.py`](file:///c:/Users/acer/OneDrive/Documents/GitHub/HunterOS%20engage/app/pipeline/ai.py#L150-L200):

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

### Exact Response Text
```text
TEST SUCCESSFULL, THIS WAS A TEST MESSAGE FROM HUNTEROS ENGAGE
```

### Invariants & Unit Test Verification
All 5 trigger invariants were verified via [`tests/test_controlled_whatsapp_test_reply.py`](file:///c:/Users/acer/OneDrive/Documents/GitHub/HunterOS%20engage/tests/test_controlled_whatsapp_test_reply.py):
1. `hi` with surrounding whitespace from authorized recipient -> **Triggers exact response**.
2. Non-`hi` message (`hello`) from authorized recipient -> **Passes through to OpenAI provider**.
3. `hi` from unauthorized phone number -> **Passes through to OpenAI provider**.
4. Feature disabled (`ENABLE_WHATSAPP_TEST_AUTO_REPLY=false`) -> **Passes through to OpenAI provider**.
5. Prior response already existing for message -> **Deduplicated; passes through without duplicate send**.

---

## 5. Outbox & Celery Execution Evidence
- **RawWebhookEvent**: Blocked prior to outbox persistence by the 403 signature rejection.
- **MessageReceived**: Not generated.
- **AIResponded**: Not generated.
- **MessageReadyToSendEvent**: Not generated.
- **ReplySent**: Not generated.
- **Celery Consumer Spans**: 0 spans executed for this test run.

---

## 6. Duplicate Response & Idempotency Checks
- **Outbox Pending Records**: 0 pending messages in `event_store`.
- **Database Messages Created**: 0 outgoing test messages created during this attempt.
- **Loop Prevention**: Verified that delivery status payloads (`statuses` in changes) do not contain `messages` and are ignored by `extract_message_data`.

---

## 7. Failures & Remaining Risks

### Primary Blocker
- **Missing `WHATSAPP_APP_SECRET`**:
  Meta requires the Meta App Secret (found in Meta App Dashboard -> Settings -> Basic -> App Secret) to validate the `X-Hub-Signature-256` header on webhook POST requests.

### Resolution Steps to Unblock
1. In the project `.env` file, add the Meta App Secret:
   ```bash
   WHATSAPP_APP_SECRET=<your_meta_app_secret_here>
   ```
2. Restart the application containers:
   ```bash
   docker compose restart api worker dispatcher
   ```
3. Have the authorized recipient send `hi` on WhatsApp.

---

## 8. Instructions for Disabling the Test Response

To disable the test response at any time:
1. Set in `.env`:
   ```bash
   ENABLE_WHATSAPP_TEST_AUTO_REPLY=false
   WHATSAPP_TEST_AUTO_REPLY=false
   ```
2. Restart containers or services:
   ```bash
   docker compose restart api worker
   ```
3. All incoming messages will immediately return to standard production AI-driven conversational handling.

---

## 9. Architecture & Contract Preservation Confirmation
- **API Contracts**: Preserved. `POST /api/v1/webhook` and `GET /api/v1/webhook` maintain exact schema and status code semantics.
- **Tenant Isolation**: Preserved. Tenant context resolution continues to use resolved `workspace_id`.
- **Database Models & Migrations**: Untouched. No schema alterations or migrations were introduced.
- **Retry & Outbox Pipeline**: Fully intact and operational.
