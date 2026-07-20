# HunterOS Engage

AI-Powered Customer Engagement Platform — Phase 1

## What This Is

HunterOS Engage is a production-grade AI communication service. In Phase 1, it receives WhatsApp messages, generates intelligent AI responses via OpenAI, and persists every conversation to PostgreSQL.

## Architecture

```
WhatsApp → FastAPI (/api/v1/webhook) → Pipeline → OpenAI → WhatsApp
                                           ↓
                                      PostgreSQL
```

## Project Structure

```
app/
├── api/v1/webhook.py          # Versioned route (thin layer)
├── domain/
│   ├── conversations/         # Models, schemas, message_service
│   ├── customers/             # Stub (Phase 2)
│   ├── leads/                 # Stub (Phase 3)
│   └── memory/                # Stub (Phase 2)
├── integrations/
│   ├── openai/client.py       # OpenAI Responses API
│   ├── whatsapp/client.py     # WhatsApp Cloud API
│   ├── postgres/database.py   # Async SQLAlchemy
│   └── meta/webhook.py        # Payload parsing & verification
├── pipeline/
│   ├── receive.py             # Stage 1: Parse & dedup
│   ├── intent.py              # Stage 2: Stub (Phase 3)
│   ├── memory.py              # Stage 3: Stub (Phase 2)
│   ├── ai.py                  # Stage 4: OpenAI call
│   ├── followup.py            # Stage 5: Stub (Phase 4)
│   └── respond.py             # Stage 6: Send reply
├── events/                    # Event-driven bus
├── prompts/v1.txt             # Editable system prompt
└── utils/                     # Logger, helpers
```

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+
- A Meta Developer App with WhatsApp Business Cloud API enabled

### 2. Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your real credentials
```

### 4. Database Migrations

```bash
alembic upgrade head
```

Or in development, the app auto-creates tables on startup.

### 5. Run the Server

```bash
uvicorn app.main:app --reload
```

### 6. Expose Locally via ngrok (for Meta webhook registration)

```bash
ngrok http 8000
```

Register `https://<ngrok-url>/api/v1/webhook` as your Meta webhook URL.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/webhook` | Meta webhook verification |
| POST | `/api/v1/webhook` | Receive WhatsApp messages |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI (dev only) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `OPENAI_MODEL` | ✅ | Model name (default: `gpt-4o`) |
| `WHATSAPP_ACCESS_TOKEN` | ✅ | Meta permanent access token |
| `WHATSAPP_PHONE_NUMBER_ID` | ✅ | WhatsApp phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | ✅ | Custom webhook verify token |
| `DATABASE_URL` | ✅ | Async PostgreSQL DSN |
| `APP_ENV` | ✅ | `development` or `production` |
| `LOG_LEVEL` | ✅ | `DEBUG`, `INFO`, `WARNING` |
| `ACTIVE_PROMPT_VERSION` | ✅ | Prompt file version (e.g. `v1`) |

## Testing

```bash
pytest tests/ -v
```

## Logging

Structured logs via `structlog`:
- **Development**: colored console output
- **Production**: JSON lines (pipe to any log aggregator)

Key log events: `webhook_verified`, `incoming_message_received`, `ai_processing_started`, `ai_processing_completed`, `database_insert_successful`, `reply_sent`, `webhook_processing_error`

## Phase Roadmap

| Phase | Feature |
|-------|---------|
| **1**  | WhatsApp + OpenAI + PostgreSQL pipeline |
| 2 | Customer Memory & Profiles |
| 3 | Intent Detection & Lead Scoring |
| 4 | Follow-up Engine & Scheduling |
| 5 | Live Dashboard & Analytics |
| 6 | Industry Modules (Real Estate, Healthcare) |
