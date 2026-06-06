"""WebSocket для обновлений мониторинга в реальном времени."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.auth import decode_user_id
from app.services.ws_hub import monitoring_ws

router = APIRouter(tags=["websocket"])


async def _handle_ws(websocket: WebSocket, token: str | None) -> None:
    if not token:
        await websocket.close(code=4401, reason="token required")
        return
    user_id = decode_user_id(token)
    if user_id is None:
        await websocket.close(code=4401, reason="invalid token")
        return

    await monitoring_ws.connect(websocket)
    ping_task = asyncio.create_task(monitoring_ws.ping_loop(websocket))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        await monitoring_ws.disconnect(websocket)


@router.websocket("/monitoring")
async def ws_monitoring(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    await _handle_ws(websocket, token)


@router.websocket("")
async def ws_root(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    await _handle_ws(websocket, token)
