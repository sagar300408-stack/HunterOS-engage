import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.utils.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ConnectionManager:
    """Redis Pub/Sub backed WebSocket broadcaster scoped by workspace."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._workspace_connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._redis = None
        self._pubsub = None
        self._listener_task = None
        
    async def startup(self):
        try:
            from app.domain.reliability.engines.caching import get_redis
            self._redis = get_redis()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe("hunteros:ws_broadcasts")
            self._listener_task = asyncio.create_task(self._listen_to_redis())
            logger.info("WebSocket Manager connected to Redis Pub/Sub")
        except Exception as e:
            logger.error(f"Failed to connect WebSocket manager to Redis: {e}")

    async def _listen_to_redis(self):
        if not self._pubsub:
            return
            
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    workspace_id_str = data.get("_workspace_id")
                    
                    if workspace_id_str:
                        workspace_id = UUID(workspace_id_str)
                        await self._local_broadcast_to_workspace(workspace_id, data)
                    else:
                        await self._local_broadcast(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis PubSub listener error: {e}")
            # Could attempt reconnect here

    async def shutdown(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.unsubscribe("hunteros:ws_broadcasts")
            await self._pubsub.close()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket, workspace_id: UUID = None) -> None:
        await websocket.accept()
        
        # Ensure redis is connected
        if self._redis is None:
            await self.startup()
            
        async with self._lock:
            self._connections.add(websocket)
            if workspace_id:
                self._workspace_connections[workspace_id].add(websocket)
                # Attach for easier disconnect handling
                websocket.state.workspace_id = workspace_id
        logger.info(
            "ws_client_connected",
            total=self.connection_count,
            client=websocket.client,
        )

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        workspace_id = getattr(websocket.state, "workspace_id", None)
        if workspace_id and workspace_id in self._workspace_connections:
            self._workspace_connections[workspace_id].discard(websocket)
            if not self._workspace_connections[workspace_id]:
                del self._workspace_connections[workspace_id]
        logger.info(
            "ws_client_disconnected",
            total=self.connection_count,
        )

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Publish a JSON payload to all connected dashboard clients via Redis."""
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        
        if self._redis:
            await self._redis.publish("hunteros:ws_broadcasts", json.dumps(payload, default=str))
        else:
            await self._local_broadcast(payload)

    async def broadcast_to_workspace(self, workspace_id: UUID, payload: dict[str, Any]) -> None:
        """Publish a JSON payload to all connected dashboard clients in a specific workspace via Redis."""
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        payload["_workspace_id"] = str(workspace_id)
        
        if self._redis:
            await self._redis.publish("hunteros:ws_broadcasts", json.dumps(payload, default=str))
        else:
            await self._local_broadcast_to_workspace(workspace_id, payload)
            
    async def _local_broadcast(self, payload: dict[str, Any]) -> None:
        # Remove routing key if present
        payload.pop("_workspace_id", None)
        message = json.dumps(payload, default=str)

        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

        if dead:
            logger.debug("ws_dead_connections_removed", count=len(dead))

    async def _local_broadcast_to_workspace(self, workspace_id: UUID, payload: dict[str, Any]) -> None:
        if workspace_id not in self._workspace_connections:
            return

        payload.pop("_workspace_id", None)
        message = json.dumps(payload, default=str)

        dead: list[WebSocket] = []
        for ws in list(self._workspace_connections[workspace_id]):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

        if dead:
            logger.debug("ws_dead_connections_removed", count=len(dead))

    async def send_to(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        """Send a JSON payload to a single client."""
        try:
            await websocket.send_text(json.dumps(payload, default=str))
        except Exception:
            self.disconnect(websocket)


# ── Singleton ──────────────────────────────────────────────────────────────────
ws_manager = ConnectionManager()
