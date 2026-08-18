import datetime
from typing import Dict, Any, Tuple, Optional, List
import httpx

from app.domain.integration.connectors.base import BaseConnector
from app.domain.integration.models import ConnectionStatus
from app.domain.integration.schemas import ConnectorMetadata, ConnectorCapabilities
from app.domain.scheduling.availability_engine import BusySlot


class OutlookCalendarConnector(BaseConnector):
    """
    Microsoft Outlook / Graph API Calendar Connector using httpx for direct API communication.
    """

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="outlook_calendar_v1",
            connector_type="calendar",
            provider="microsoft",
            name="Outlook Calendar",
            version="1.0.0",
            description="Microsoft Graph API integration for booking and availability.",
            capabilities=ConnectorCapabilities(supports_read=True, supports_write=True, supports_webhooks=False),
            authentication_type="oauth2",
            supported_actions=["create_event"],
            supported_events=["calendar_synced"]
        )

    async def _refresh_token(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refreshes the access token if needed.
        """
        refresh_token = credentials.get("refresh_token")
        if not refresh_token:
            raise ValueError("No refresh token available")

        from app.config import get_settings
        app_settings = get_settings()
        client_id = app_settings.microsoft_client_id or (settings.get("client_id") if settings else None)
        client_secret = app_settings.microsoft_client_secret or (settings.get("client_secret") if settings else None)

        if not client_id or not client_secret:
            raise ValueError("OAuth client credentials missing")

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data)
            resp.raise_for_status()
            new_tokens = resp.json()

        # Preserve refresh_token if not returned
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        
        return new_tokens

    async def _execute_with_refresh(self, api_call_coro, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[Any, Optional[Dict[str, Any]]]:
        """
        Executes a callable that makes an HTTP request.
        If it fails with 401, refreshes the token EXACTLY once and retries.
        Returns (result, new_credentials)
        """
        try:
            return await api_call_coro(credentials.get("access_token")), None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                new_creds = await self._refresh_token(credentials, settings)
                return await api_call_coro(new_creds.get("access_token")), new_creds
            raise

    async def health_check(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        if not credentials.get("access_token"):
            return ConnectionStatus.ERROR.value, "Missing access token"

        async def _call(token: str):
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                r.raise_for_status()
                return r

        try:
            await self._execute_with_refresh(_call, credentials, settings)
            return ConnectionStatus.CONNECTED.value, None
        except Exception as e:
            return ConnectionStatus.ERROR.value, str(e)

    async def execute_action(self, action_name: str, payload: Dict[str, Any], credentials: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes a supported action, such as create_event.
        Idempotency: actively searches Microsoft Graph for the hunteros_id using $filter before creating.
        """
        if action_name == "create_event":
            calendar_id = settings.get("calendar_id") if settings else None
            base_url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}" if calendar_id else "https://graph.microsoft.com/v1.0/me"
            event_id = str(payload.get("event_id"))

            async def _check_and_create(token: str):
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                async with httpx.AsyncClient() as client:
                    # 1. Reconciliation (Duplicate Prevention)
                    search_url = f"{base_url}/events"
                    # Graph API requires a specific format for extended properties
                    filter_query = f"singleValueExtendedProperties/Any(ep: ep/id eq 'String {{66f5a359-4659-4830-9070-00040ec6ac6e}} Name hunteros_id' and ep/value eq '{event_id}')"
                    search_params = {"$filter": filter_query}
                    
                    search_resp = await client.get(search_url, headers=headers, params=search_params)
                    search_resp.raise_for_status()
                    search_data = search_resp.json()

                    if search_data.get("value"):
                        # Event already exists
                        existing = search_data["value"][0]
                        return existing["id"]

                    # 2. Creation
                    ms_event = {
                        "subject": payload.get("title"),
                        "body": {
                            "contentType": "HTML",
                            "content": payload.get("description")
                        },
                        "start": {
                            "dateTime": payload.get("start_time"),
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": payload.get("end_time"),
                            "timeZone": "UTC"
                        },
                        "singleValueExtendedProperties": [
                            {
                                "id": "String {66f5a359-4659-4830-9070-00040ec6ac6e} Name hunteros_id",
                                "value": event_id
                            }
                        ]
                    }
                    create_resp = await client.post(search_url, headers=headers, json=ms_event)
                    create_resp.raise_for_status()
                    return create_resp.json()["id"]

            try:
                external_id, new_creds = await self._execute_with_refresh(_check_and_create, credentials, settings)
                res = {"status": "success", "external_id": external_id, "action": action_name}
                if new_creds:
                    res["new_credentials"] = new_creds
                return res
            except Exception as e:
                return {"status": "error", "error": str(e), "action": action_name}

        raise ValueError(f"Action {action_name} not supported by OutlookCalendarConnector")

    async def get_busy_slots(self, credentials: Dict[str, Any], start_time: datetime.datetime, end_time: datetime.datetime, settings: Dict[str, Any] = None) -> List[BusySlot]:
        """
        Fetch busy slots from Microsoft Graph API (calendarView endpoint).
        """
        calendar_id = settings.get("calendar_id") if settings else None
        base_url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}" if calendar_id else "https://graph.microsoft.com/v1.0/me"

        async def _fetch(token: str):
            headers = {"Authorization": f"Bearer {token}"}
            # Microsoft expects ISO strings
            params = {
                "startDateTime": start_time.isoformat(),
                "endDateTime": end_time.isoformat()
            }
            async with httpx.AsyncClient() as client:
                # Use calendarView to expand recurring events properly
                resp = await client.get(f"{base_url}/calendarView", headers=headers, params=params)
                resp.raise_for_status()
                return resp.json()

        try:
            data, new_creds = await self._execute_with_refresh(_fetch, credentials, settings)
            events = data.get("value", [])
            
            slots = []
            for e in events:
                # Omit "free" availability statuses
                if e.get("showAs") == "free":
                    continue
                # MS Graph returns UTC times with 'Z'
                st_str = e["start"]["dateTime"].replace('Z', '+00:00')
                et_str = e["end"]["dateTime"].replace('Z', '+00:00')
                # If they have a different timezone specified, we'd need to parse it, 
                # but calendarView usually returns UTC if we don't specify Prefer header, or based on Prefer header.
                st = datetime.datetime.fromisoformat(st_str)
                et = datetime.datetime.fromisoformat(et_str)
                # Ensure they have timezone info
                if st.tzinfo is None:
                    st = st.replace(tzinfo=datetime.timezone.utc)
                if et.tzinfo is None:
                    et = et.replace(tzinfo=datetime.timezone.utc)
                slots.append(BusySlot(start=st, end=et))
                
            return slots
        except Exception:
            return []

    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        return []

    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        return []
