import uuid
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger("websocket.kitchen")


class ConnectionManager:
    """Process-wide registry of kitchen-display WebSocket connections,
    grouped by location. Single-process only: broadcasting a status change
    to N kitchen screens works because they're all connected to this same
    worker. If the app is ever run with multiple worker processes, this
    needs to move to a shared pub/sub (e.g. Redis) instead."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, location_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[location_id].add(websocket)

    def disconnect(self, location_id: uuid.UUID, websocket: WebSocket) -> None:
        self._connections[location_id].discard(websocket)
        if not self._connections[location_id]:
            self._connections.pop(location_id, None)

    async def broadcast(self, location_id: uuid.UUID, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for websocket in self._connections.get(location_id, ()):
            try:
                await websocket.send_json(message)
            except Exception:
                logger.warning("Dropping dead kitchen websocket connection", exc_info=True)
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(location_id, websocket)


kitchen_ws_manager = ConnectionManager()
