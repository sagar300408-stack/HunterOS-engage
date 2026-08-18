import datetime
from typing import Dict, Any, Tuple, Optional, List
import httpx
import json

from app.domain.integration.connectors.base import BaseConnector
from app.domain.integration.models import ConnectionStatus
from app.domain.integration.schemas import ConnectorMetadata, ConnectorCapabilities
from app.domain.scheduling.availability_engine import BusySlot


class GoogleCalendarConnector(BaseConnector):
    """
    Google Calendar Connector using httpx for direct API communication.
    """

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="google_calendar_v1",
            connector_type="calendar",
            provider="google",
            name="Google Calendar",
            version="1.0.0",
            description="Google Calendar integration for booking and availability.",
            capabilities=ConnectorCapabilities(supports_read=True, supports_write=True, supports_webhooks=False),
            authentication_type="oauth2",
            supported_actions=["create_event"],
            supported_events=["calendar_synced"]
        )

    async def _refresh_token(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refreshes the access token if needed. 
        Note: The integration engine handles persisting the returned new_credentials to the DB.
        If `new_credentials` is returned, the engine will update the CredentialProvider.
        """
        refresh_token = credentials.get("refresh_token")
        if not refresh_token:
            raise ValueError("No refresh token available")

        from app.config import get_settings
        app_settings = get_settings()
        client_id = app_settings.google_client_id or (settings.get("client_id") if settings else None)
        client_secret = app_settings.google_client_secret or (settings.get("client_secret") if settings else None)

        if not client_id or not client_secret:
            raise ValueError("OAuth client credentials missing")

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data=data)
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
                # 401 handling: Exactly 1 refresh + 1 retry
                new_creds = await self._refresh_token(credentials, settings)
                return await api_call_coro(new_creds.get("access_token")), new_creds
            raise

    async def health_check(self, credentials: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        if not credentials.get("access_token"):
            return ConnectionStatus.ERROR.value, "Missing access token"
        
        async def _call(token: str):
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://www.googleapis.com/calendar/v3/users/me/calendarList",
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
        Idempotency: actively searches Google for the hunteros_id before creating.
        Returns a payload containing new_credentials if a refresh occurred.
        """
        if action_name == "create_event":
            calendar_id = settings.get("calendar_id", "primary") if settings else "primary"
            event_id = str(payload.get("event_id"))
            
            async def _check_and_create(token: str):
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                async with httpx.AsyncClient() as client:
                    # 1. Reconciliation (Duplicate Prevention)
                    search_url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
                    search_params = {"privateExtendedProperty": f"hunteros_id={event_id}"}
                    search_resp = await client.get(search_url, headers=headers, params=search_params)
                    search_resp.raise_for_status()
                    search_data = search_resp.json()
                    
                    if search_data.get("items"):
                        # Event already exists
                        existing = search_data["items"][0]
                        return existing["id"]

                    # 2. Creation
                    google_event = {
                        "summary": payload.get("title"),
                        "description": payload.get("description"),
                        "start": {"dateTime": payload.get("start_time")},
                        "end": {"dateTime": payload.get("end_time")},
                        "extendedProperties": {
                            "private": {
                                "hunteros_id": event_id
                            }
                        }
                    }
                    create_resp = await client.post(search_url, headers=headers, json=google_event)
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

        raise ValueError(f"Action {action_name} not supported by GoogleCalendarConnector")

    async def get_busy_slots(self, credentials: Dict[str, Any], start_time: datetime.datetime, end_time: datetime.datetime, settings: Dict[str, Any] = None) -> List[BusySlot]:
        """
        Fetch busy slots from Google Calendar API (freebusy endpoint).
        """
        calendar_id = settings.get("calendar_id", "primary") if settings else "primary"
        
        async def _fetch(token: str):
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {
                "timeMin": start_time.isoformat(),
                "timeMax": end_time.isoformat(),
                "items": [{"id": calendar_id}]
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://www.googleapis.com/calendar/v3/freeBusy", headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()

        try:
            data, new_creds = await self._execute_with_refresh(_fetch, credentials, settings)
            calendars = data.get("calendars", {})
            cal_data = calendars.get(calendar_id, {})
            busy_periods = cal_data.get("busy", [])
            
            slots = []
            for b in busy_periods:
                st = datetime.datetime.fromisoformat(b["start"].replace('Z', '+00:00'))
                et = datetime.datetime.fromisoformat(b["end"].replace('Z', '+00:00'))
                slots.append(BusySlot(start=st, end=et))
            # Note: We return new_creds as well if needed by the caller, but the availability_engine
            # signature does not currently support returning new_credentials easily. 
            # In a full system, an out-of-band credential update task could handle this.
            return slots
        except Exception:
            return []

    async def sync_events(self, credentials: Dict[str, Any], last_sync: Any) -> list:
        return []

    async def parse_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> list:
        return []
