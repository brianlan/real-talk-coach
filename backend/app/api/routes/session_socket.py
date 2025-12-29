from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class SessionSocketHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        self._connections[session_id].discard(websocket)
        if not self._connections[session_id]:
            self._connections.pop(session_id, None)

    async def broadcast(self, session_id: str, payload: dict[str, Any]) -> None:
        if session_id not in self._connections:
            return
        message = json.dumps(payload)
        for socket in list(self._connections[session_id]):
            await socket.send_text(message)


hub = SessionSocketHub()


@router.websocket("/ws/sessions/{session_id}")
async def session_socket(websocket: WebSocket, session_id: str):
    await hub.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(session_id, websocket)
