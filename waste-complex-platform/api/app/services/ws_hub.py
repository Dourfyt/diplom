"""WebSocket-хаб для push-событий мониторинга в реальном времени."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MonitoringWSHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, ensure_ascii=False)
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.discard(ws)

    async def notify_batch_updated(self, batch_id: int) -> None:
        await self.broadcast({"type": "batch_updated", "batch_id": batch_id})

    async def notify_deviation_created(self, batch_id: int, deviation_id: int) -> None:
        await self.broadcast(
            {
                "type": "deviation_created",
                "batch_id": batch_id,
                "deviation_id": deviation_id,
            }
        )

    async def ping_loop(self, websocket: WebSocket, interval: float = 30.0) -> None:
        try:
            while True:
                await asyncio.sleep(interval)
                await websocket.send_text(json.dumps({"type": "ping"}))
        except asyncio.CancelledError:
            return
        except Exception:
            return


monitoring_ws = MonitoringWSHub()


def schedule_ws(coro) -> None:
    """Запустить coroutine WS-рассылки из синхронного обработчика FastAPI."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def schedule_batch_updated(batch_id: int) -> None:
    schedule_ws(monitoring_ws.notify_batch_updated(batch_id))


def schedule_deviation_created(batch_id: int, deviation_id: int) -> None:
    schedule_ws(monitoring_ws.notify_deviation_created(batch_id, deviation_id))
