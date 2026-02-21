"""
NERVE — Live WebSocket Feed
Broadcasts REAL events from the scraper to all connected clients.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from engine.scraper import on_event

router = APIRouter(tags=["WebSocket"])

# ── Connection manager ───────────────────────────────────────────────

_connections: list[WebSocket] = []
_event_queue: asyncio.Queue = asyncio.Queue(maxsize=500)


def _on_scraper_event(event: dict):
    """Callback registered with the scraper — queues real events."""
    try:
        _event_queue.put_nowait(event)
    except asyncio.QueueFull:
        pass  # drop oldest if queue is full


# Register with scraper
on_event(_on_scraper_event)


async def _broadcast(payload: str):
    """Send to all connected clients."""
    dead = []
    for ws in _connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)


async def _event_dispatcher():
    """Background task: reads from event queue and broadcasts."""
    while True:
        event = await _event_queue.get()
        payload = json.dumps(event, default=str)
        await _broadcast(payload)


# ── Start dispatcher ─────────────────────────────────────────────────

_dispatcher_task: asyncio.Task | None = None


def ensure_dispatcher():
    global _dispatcher_task
    if _dispatcher_task is None or _dispatcher_task.done():
        _dispatcher_task = asyncio.create_task(_event_dispatcher())


# ── WebSocket endpoint ───────────────────────────────────────────────

@router.websocket("/ws/feed")
async def websocket_feed(ws: WebSocket):
    """WebSocket for real-time event stream from NERVE scraper."""
    await ws.accept()
    _connections.append(ws)
    ensure_dispatcher()

    # Welcome message with live scraper status
    from engine.scraper import get_scraper_status
    status = get_scraper_status()

    await ws.send_text(json.dumps({
        "type": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "NERVE live WebSocket feed",
        "scraper_status": status,
        "active_clients": len(_connections),
    }))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _connections.remove(ws)
