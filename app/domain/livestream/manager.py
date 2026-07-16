import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebSocketConnectionManager:
    """
    Thread-safe in-memory WebSocket broadcaster.
    Strictly enforces workspace isolation by partitioning connections by workspace_id.
    """

    def __init__(self) -> None:
        # workspace_id -> set of active WebSockets
        self._workspaces: Dict[UUID, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    @property
    def total_connection_count(self) -> int:
        return sum(len(conns) for conns in self._workspaces.values())

    async def connect(self, workspace_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            if workspace_id not in self._workspaces:
                self._workspaces[workspace_id] = set()
            self._workspaces[workspace_id].add(websocket)
            
        logger.info(
            "livestream_client_connected",
            workspace_id=str(workspace_id),
            total_global=self.total_connection_count,
            workspace_total=len(self._workspaces[workspace_id])
        )

    async def disconnect(self, workspace_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            if workspace_id in self._workspaces:
                self._workspaces[workspace_id].discard(websocket)
                if not self._workspaces[workspace_id]:
                    del self._workspaces[workspace_id]
                    
        logger.info(
            "livestream_client_disconnected",
            workspace_id=str(workspace_id),
            total_global=self.total_connection_count
        )

    async def broadcast_to_workspace(self, workspace_id: UUID, payload: dict[str, Any]) -> None:
        """Send a JSON payload only to connected clients in the specified workspace."""
        if workspace_id not in self._workspaces or not self._workspaces[workspace_id]:
            return

        # Add server timestamp
        payload.setdefault("timestamp", datetime.utcnow().isoformat())
        message = json.dumps(payload, default=str)

        dead: list[WebSocket] = []
        # Copy the set to avoid RuntimeError: Set changed size during iteration
        connections = list(self._workspaces[workspace_id])
        
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            await self.disconnect(workspace_id, ws)

        if dead:
            logger.debug("livestream_dead_connections_removed", count=len(dead), workspace_id=str(workspace_id))

    async def send_to(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        """Send a JSON payload to a single client (mostly for acks/pings)."""
        try:
            await websocket.send_text(json.dumps(payload, default=str))
        except Exception:
            # We don't have the workspace_id here, but we can't cleanly remove it.
            # It will be caught and removed on the next broadcast.
            pass


# Singleton instance
livestream_manager = WebSocketConnectionManager()
