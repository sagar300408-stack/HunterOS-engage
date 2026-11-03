import abc
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

logger = logging.getLogger("hunteros.integration.email_auth.provider")


# ── Custom Exceptions ─────────────────────────────────────────────────────────

class EmailOAuthError(Exception):
    """Base exception for email provider OAuth operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class OAuthCodeExchangeError(EmailOAuthError):
    """Raised when authorization code exchange fails."""
    pass


class OAuthScopeError(EmailOAuthError):
    """Raised when required scopes are missing or insufficient."""
    pass


class OAuthIdentityError(EmailOAuthError):
    """Raised when retrieving authenticated account identity fails."""
    pass


class OAuthTokenRefreshError(EmailOAuthError):
    """Raised when refreshing access token fails."""
    pass


class OAuthReauthRequiredError(OAuthTokenRefreshError):
    """Raised when refresh token is invalid or revoked (user must re-authenticate)."""
    pass


class OAuthNetworkError(EmailOAuthError):
    """Raised when provider cannot be contacted due to network/server failure."""
    pass


# ── Base Abstract Provider ───────────────────────────────────────────────────

class BaseEmailOAuthProvider(abc.ABC):
    """
    Common abstraction for email provider OAuth authentication.
    Handles URL generation, code exchange, scope validation, identity extraction,
    token refresh, and connectivity checks across Google and Microsoft.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Name of provider: 'google' or 'microsoft'."""
        pass

    @property
    @abc.abstractmethod
    def required_scopes(self) -> Set[str]:
        """Set of required scopes."""
        pass

    @abc.abstractmethod
    def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        state_token: str,
        prompt: str = "consent",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generates the provider-specific OAuth authorization URL."""
        pass

    @abc.abstractmethod
    async def exchange_code(
        self,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens."""
        pass

    @abc.abstractmethod
    async def refresh_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Refreshes an expired access token."""
        pass

    @abc.abstractmethod
    async def get_account_identity(self, access_token: str) -> Dict[str, Any]:
        """
        Retrieves real authenticated account identity from provider API.
        Must return normalized dict:
        {
            "email": str,
            "display_name": Optional[str],
            "provider_account_id": Optional[str],
            "metadata": Dict[str, Any]
        }
        """
        pass

    @abc.abstractmethod
    async def check_connectivity(self, access_token: str) -> Tuple[bool, Optional[str]]:
        """
        Validates real mailbox connectivity with granted access token.
        Returns (is_connected: bool, error_message: Optional[str]).
        """
        pass

    def validate_scopes(self, granted_scope_str: str) -> Tuple[bool, Set[str]]:
        """
        Validates granted scope string against required_scopes.
        Returns (is_valid: bool, missing_scopes: Set[str]).
        """
        if not granted_scope_str:
            return False, set(self.required_scopes)

        granted_set = set(granted_scope_str.split())
        missing = set(self.required_scopes) - granted_set
        return len(missing) == 0, missing


# ── Google Gmail Provider ─────────────────────────────────────────────────────

class GoogleGmailOAuthProvider(BaseEmailOAuthProvider):
    """
    Google Gmail OAuth 2.0 implementation.
    Requests calendar.events, gmail.readonly, and gmail.send scopes.
    Uses Gmail REST API v1 for identity and mailbox verification.
    """

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
    GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
    GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
    USERINFO_EMAIL_SCOPE = "https://www.googleapis.com/auth/userinfo.email"

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def required_scopes(self) -> Set[str]:
        return {
            self.CALENDAR_SCOPE,
            self.GMAIL_READONLY_SCOPE,
            self.GMAIL_SEND_SCOPE,
        }

    def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        state_token: str,
        prompt: str = "consent",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> str:
        # Include calendar + gmail scopes
        scopes_list = [
            self.CALENDAR_SCOPE,
            self.GMAIL_READONLY_SCOPE,
            self.GMAIL_SEND_SCOPE,
            self.USERINFO_EMAIL_SCOPE,
        ]
        params = {
            "client_id": client_id,
            "response_type": "code",
            "scope": " ".join(scopes_list),
            "redirect_uri": redirect_uri,
            "state": state_token,
            "access_type": "offline",
            "prompt": prompt,
            "include_granted_scopes": "true",
        }
        if extra_params:
            params.update(extra_params)
        return f"{self.GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(
        self,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if extra_params:
            data.update(extra_params)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.GOOGLE_TOKEN_URL, data=data)
        except Exception as e:
            logger.error("Google token exchange network error")
            raise OAuthNetworkError(f"Network error communicating with Google: {e}")

        if resp.status_code != 200:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_desc = error_data.get("error_description") or error_data.get("error") or resp.text
            logger.error(f"Google code exchange failed ({resp.status_code}): {error_desc}")
            raise OAuthCodeExchangeError(f"Google token exchange failed: {error_desc}", details=error_data)

        return resp.json()

    async def refresh_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        if extra_params:
            data.update(extra_params)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.GOOGLE_TOKEN_URL, data=data)
        except Exception as e:
            logger.error("Google token refresh network error")
            raise OAuthNetworkError(f"Network error communicating with Google token endpoint: {e}")

        if resp.status_code != 200:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            err_code = error_data.get("error", "")
            err_desc = error_data.get("error_description", "") or resp.text
            
            if err_code in ["invalid_grant", "unauthorized_client"] or "revoked" in err_desc.lower():
                logger.warning(f"Google refresh token revoked or invalid: {err_code} - {err_desc}")
                raise OAuthReauthRequiredError(f"Google authorization revoked: {err_desc}", details=error_data)
                
            logger.error(f"Google token refresh failed ({resp.status_code}): {err_desc}")
            raise OAuthTokenRefreshError(f"Google token refresh failed: {err_desc}", details=error_data)

        new_tokens = resp.json()
        # Google usually does not return refresh_token on refresh; preserve original
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        return new_tokens

    async def get_account_identity(self, access_token: str) -> Dict[str, Any]:
        """Calls Gmail API profile and UserInfo endpoint to identify authenticated user."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        email_address = None
        messages_total = None
        history_id = None
        display_name = None
        account_id = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Fetch Gmail Profile
            try:
                profile_resp = await client.get(self.GOOGLE_GMAIL_PROFILE_URL, headers=headers)
                if profile_resp.status_code == 200:
                    profile_data = profile_resp.json()
                    email_address = profile_data.get("emailAddress")
                    messages_total = profile_data.get("messagesTotal")
                    history_id = profile_data.get("historyId")
            except Exception as e:
                logger.warning(f"Failed to query Gmail profile endpoint: {e}")

            # 2. Fetch UserInfo for Name/ID
            try:
                userinfo_resp = await client.get(self.GOOGLE_USERINFO_URL, headers=headers)
                if userinfo_resp.status_code == 200:
                    userinfo_data = userinfo_resp.json()
                    if not email_address:
                        email_address = userinfo_data.get("email")
                    display_name = userinfo_data.get("name")
                    account_id = userinfo_data.get("id")
            except Exception as e:
                logger.warning(f"Failed to query Google userinfo endpoint: {e}")

        if not email_address:
            logger.error("Could not determine Google account email address from provider API")
            raise OAuthIdentityError("Could not retrieve authenticated Google account identity")

        return {
            "email": email_address.lower(),
            "display_name": display_name or email_address.split("@")[0],
            "provider_account_id": account_id or email_address,
            "metadata": {
                "messages_total": messages_total,
                "history_id": history_id,
            },
        }

    async def check_connectivity(self, access_token: str) -> Tuple[bool, Optional[str]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.GOOGLE_GMAIL_PROFILE_URL, headers=headers)
                if resp.status_code == 200:
                    return True, None
                elif resp.status_code in [401, 403]:
                    return False, f"Gmail API authentication failed ({resp.status_code}): {resp.text}"
                else:
                    return False, f"Gmail API error ({resp.status_code}): {resp.text}"
        except Exception as e:
            return False, f"Connection to Gmail API failed: {e}"


# ── Microsoft Graph Provider ─────────────────────────────────────────────────

class MicrosoftGraphOAuthProvider(BaseEmailOAuthProvider):
    """
    Microsoft Graph (Outlook / Microsoft 365) OAuth 2.0 implementation.
    Requests Calendars.ReadWrite, Mail.Read, Mail.Send, User.Read, offline_access.
    Uses Microsoft Graph v1.0 /me and /me/mailFolders/inbox for verification.
    """

    MS_AUTH_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
    MS_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    MS_ME_URL = "https://graph.microsoft.com/v1.0/me"
    MS_INBOX_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox"

    CALENDAR_SCOPE = "Calendars.ReadWrite"
    MAIL_READ_SCOPE = "Mail.Read"
    MAIL_SEND_SCOPE = "Mail.Send"
    USER_READ_SCOPE = "User.Read"
    OFFLINE_ACCESS_SCOPE = "offline_access"

    def __init__(self, tenant_id: str = "common"):
        self._tenant_id = tenant_id or "common"

    @property
    def provider_name(self) -> str:
        return "microsoft"

    @property
    def required_scopes(self) -> Set[str]:
        return {
            self.CALENDAR_SCOPE,
            self.MAIL_READ_SCOPE,
            self.MAIL_SEND_SCOPE,
        }

    def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        state_token: str,
        prompt: str = "consent",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> str:
        scopes_list = [
            self.OFFLINE_ACCESS_SCOPE,
            self.USER_READ_SCOPE,
            self.CALENDAR_SCOPE,
            self.MAIL_READ_SCOPE,
            self.MAIL_SEND_SCOPE,
        ]
        base_url = self.MS_AUTH_URL_TEMPLATE.format(tenant_id=self._tenant_id)
        params = {
            "client_id": client_id,
            "response_type": "code",
            "scope": " ".join(scopes_list),
            "redirect_uri": redirect_uri,
            "state": state_token,
            "prompt": prompt,
        }
        if extra_params:
            params.update(extra_params)
        return f"{base_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code(
        self,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        token_url = self.MS_TOKEN_URL_TEMPLATE.format(tenant_id=self._tenant_id)
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if extra_params:
            data.update(extra_params)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(token_url, data=data)
        except Exception as e:
            logger.error("Microsoft token exchange network error")
            raise OAuthNetworkError(f"Network error communicating with Microsoft: {e}")

        if resp.status_code != 200:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_desc = error_data.get("error_description") or error_data.get("error") or resp.text
            logger.error(f"Microsoft code exchange failed ({resp.status_code}): {error_desc}")
            raise OAuthCodeExchangeError(f"Microsoft token exchange failed: {error_desc}", details=error_data)

        return resp.json()

    async def refresh_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        token_url = self.MS_TOKEN_URL_TEMPLATE.format(tenant_id=self._tenant_id)
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        if extra_params:
            data.update(extra_params)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(token_url, data=data)
        except Exception as e:
            logger.error("Microsoft token refresh network error")
            raise OAuthNetworkError(f"Network error communicating with Microsoft token endpoint: {e}")

        if resp.status_code != 200:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            err_code = error_data.get("error", "")
            err_desc = error_data.get("error_description", "") or resp.text

            if err_code in ["invalid_grant", "unauthorized_client"] or "revoked" in err_desc.lower():
                logger.warning(f"Microsoft refresh token revoked or invalid: {err_code} - {err_desc}")
                raise OAuthReauthRequiredError(f"Microsoft authorization revoked: {err_desc}", details=error_data)

            logger.error(f"Microsoft token refresh failed ({resp.status_code}): {err_desc}")
            raise OAuthTokenRefreshError(f"Microsoft token refresh failed: {err_desc}", details=error_data)

        new_tokens = resp.json()
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        return new_tokens

    async def get_account_identity(self, access_token: str) -> Dict[str, Any]:
        """Calls Microsoft Graph /me endpoint to identify authenticated user."""
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.MS_ME_URL, headers=headers)
        except Exception as e:
            logger.error("Microsoft Graph /me network error")
            raise OAuthNetworkError(f"Network error connecting to Microsoft Graph: {e}")

        if resp.status_code != 200:
            logger.error(f"Microsoft Graph /me failed ({resp.status_code}): {resp.text}")
            raise OAuthIdentityError(f"Microsoft Graph /me returned {resp.status_code}: {resp.text}")

        data = resp.json()
        email = data.get("mail") or data.get("userPrincipalName")
        if not email:
            raise OAuthIdentityError("Microsoft account identity missing both mail and userPrincipalName")

        return {
            "email": email.lower(),
            "display_name": data.get("displayName") or email.split("@")[0],
            "provider_account_id": data.get("id") or email,
            "metadata": {
                "user_principal_name": data.get("userPrincipalName"),
                "job_title": data.get("jobTitle"),
            },
        }

    async def check_connectivity(self, access_token: str) -> Tuple[bool, Optional[str]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test inbox folder accessibility
                resp = await client.get(self.MS_INBOX_URL, headers=headers)
                if resp.status_code == 200:
                    return True, None
                elif resp.status_code in [401, 403]:
                    # Fallback test /me if inbox folder has permissions difference
                    me_resp = await client.get(self.MS_ME_URL, headers=headers)
                    if me_resp.status_code == 200:
                        return True, None
                    return False, f"Microsoft Graph access denied ({resp.status_code}): {resp.text}"
                else:
                    return False, f"Microsoft Graph error ({resp.status_code}): {resp.text}"
        except Exception as e:
            return False, f"Connection to Microsoft Graph failed: {e}"


# ── Provider Factory ─────────────────────────────────────────────────────────

def get_email_oauth_provider(provider_name: str, tenant_id: str = "common") -> BaseEmailOAuthProvider:
    """Factory to retrieve the appropriate Email OAuth Provider."""
    normalized = provider_name.lower().strip()
    if normalized == "google":
        return GoogleGmailOAuthProvider()
    elif normalized in ["microsoft", "outlook", "azure"]:
        return MicrosoftGraphOAuthProvider(tenant_id=tenant_id)
    else:
        raise ValueError(f"Unsupported email provider: {provider_name}")
