# HunterOS Engage: Email Provider OAuth Setup Guide

This guide details the procedure for registering and configuring production OAuth 2.0 applications for **Google Gmail** and **Microsoft Outlook / Microsoft 365** within HunterOS Engage.

---

## 1. Overview & Security Architecture

HunterOS Engage connects to user mailboxes via standard delegated OAuth 2.0. All tokens are protected by a multi-layer defense model:

- **At-Rest Token Encryption:** All OAuth `access_token` and `refresh_token` payloads are encrypted before persistence in PostgreSQL using authenticated symmetric encryption (Fernet / AES-128-CBC + HMAC-SHA256).
- **Redis-Backed State Protection:** OAuth `state` parameters are generated cryptographically, stored in Redis with a 10-minute TTL, and atomically consumed (`GETDEL` / Lua script) upon callback to eliminate CSRF and replay attacks.
- **Strict Multi-Tenant Workspace Isolation:** Every integration connection is hard-bound to an authenticated `workspace_id`. Cross-tenant querying, editing, or state interception is rejected with `403 Forbidden` or `404 Not Found`.
- **Distributed Token Refresh Locks:** Redis distributed locks (`lock:email_token_refresh:{connection_id}`) prevent stampedes and race conditions when refreshing expiring tokens across clustered Celery workers or API replicas.
- **Granular Scopes:** Only the minimal scopes necessary for reading, sending, and calendar synchronization are requested.

---

## 2. Google Cloud Platform (Gmail Integration)

### Step 2.1: Create or Select a Google Cloud Project
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `HunterOS-Engage-Prod`) or select an existing project.

### Step 2.2: Enable APIs
Enable the following APIs under **APIs & Services > Library**:
- **Gmail API**
- **Google Calendar API**

### Step 2.3: Configure the OAuth Consent Screen
1. Go to **APIs & Services > OAuth consent screen**.
2. Select **User Type**:
   - **Internal** (if testing solely within a Google Workspace organization), or
   - **External** (for SaaS production access to external customer Google accounts).
3. Fill in the App Name (`HunterOS Engage`), User Support Email, and Developer Contact Email.
4. Add Scopes:
   - `https://www.googleapis.com/auth/calendar.events` (Calendar events management)
   - `https://www.googleapis.com/auth/gmail.readonly` (Read customer email and history)
   - `https://www.googleapis.com/auth/gmail.send` (Send outgoing emails)
   - `https://www.googleapis.com/auth/userinfo.email` (Identity verification)
5. Save and add Test Users if running in External/Testing mode.

> **Note on Verification:** For public production apps, Google requires OAuth verification for Restricted Scopes (`gmail.readonly`, `gmail.send`). Submit the app verification and privacy policy prior to public rollout.

### Step 2.4: Create OAuth 2.0 Client Credentials
1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Application Type: **Web application**.
4. Name: `HunterOS Engage Backend`.
5. **Authorized redirect URIs**:
   - Development: `http://localhost:8000/api/v1/integrations/oauth/callback`
   - Production: `https://<YOUR_API_DOMAIN>/api/v1/integrations/oauth/callback`
6. Click **Create**. Copy the **Client ID** and **Client Secret**.

---

## 3. Microsoft Entra ID (Outlook / Office 365)

### Step 3.1: Register an Application
1. Navigate to the [Microsoft Entra admin center](https://entra.microsoft.com/) or Azure Portal > **App registrations**.
2. Click **New registration**.
3. Name: `HunterOS Engage Mail`.
4. Supported account types:
   - Select **Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)** if serving all users.
   - Or **Accounts in this organizational directory only** for private single-tenant enterprise deployments.
5. **Redirect URI**:
   - Platform: **Web**.
   - URI: `https://<YOUR_API_DOMAIN>/api/v1/integrations/oauth/callback` (or `http://localhost:8000/api/v1/integrations/oauth/callback` for dev).
6. Click **Register**. Copy the **Application (client) ID**.

### Step 3.2: Configure API Permissions
1. Go to **API permissions > Add a permission > Microsoft Graph > Delegated permissions**.
2. Select and add the following permissions:
   - `offline_access` (Required for refresh tokens)
   - `User.Read` (Read user profile and email address)
   - `Calendars.ReadWrite` (Calendar events access)
   - `Mail.Read` (Read user mailbox messages and folders)
   - `Mail.Send` (Send mail on user's behalf)
3. Click **Add permissions**.

### Step 3.3: Create Client Secret
1. Go to **Certificates & secrets > Client secrets > New client secret**.
2. Description: `HunterOS Production Secret`.
3. Select an expiry period (e.g., 12 or 24 months).
4. Click **Add**. **Immediately copy the Secret Value** (it will be masked after leaving the page).

---

## 4. Environment Variables Configuration

Configure the following variables in your `.env` or deployment secrets store:

```bash
# Fernet Encryption Key (Mandatory for credential security)
# Generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
OAUTH_ENCRYPTION_KEY="<base64-encoded-fernet-key>"

# Redis (State storage, token refresh locks, Celery broker)
REDIS_URL="redis://localhost:6379/0"

# Google OAuth
GOOGLE_CLIENT_ID="<your-google-client-id>.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="<your-google-client-secret>"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/integrations/oauth/callback"

# Microsoft OAuth
MICROSOFT_CLIENT_ID="<your-microsoft-app-id-guid>"
MICROSOFT_CLIENT_SECRET="<your-microsoft-client-secret-value>"
MICROSOFT_TENANT_ID="common"  # Use 'common' for multi-tenant / personal accounts, or your Azure Tenant ID
MICROSOFT_REDIRECT_URI="http://localhost:8000/api/v1/integrations/oauth/callback"
```

---

## 5. Connection Management API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/integrations/email/{provider}/authorize` | Initiates OAuth flow, creates a `PENDING` connection, stores Redis state, and returns provider `authorize_url`. |
| `GET` | `/api/v1/integrations/oauth/callback` | OAuth redirect target. Atomically validates state, exchanges code, verifies scopes, extracts user email identity, encrypts credentials, and activates connection (`CONNECTED`). |
| `GET` | `/api/v1/integrations/email/status` | Lists all active and pending email accounts for the tenant. Never exposes tokens or secrets. |
| `POST` | `/api/v1/integrations/{id}/health-check` | Tests live mailbox connectivity upstream. Performs auto-refresh if token is expired. |
| `POST` | `/api/v1/integrations/{id}/refresh` | Manually forces token refresh with Redis distributed lock. Updates DB state. |
| `POST` | `/api/v1/integrations/{id}/disconnect` | Wipes encrypted tokens from database and sets status to `DISCONNECTED`. |
