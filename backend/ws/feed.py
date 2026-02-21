"""
NERVE — WebSocket Feed
Envoie les events temps reel au dashboard de William.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])

# ── Gestionnaire de connexions ───────────────────────────────────────

_connections: list[WebSocket] = []


async def broadcast(event: dict[str, Any]):
    """Envoie un event a tous les clients connectes."""
    payload = json.dumps(event, default=str)
    dead = []
    for ws in _connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)


# ── Generateur d'events pour la demo ─────────────────────────────────

_AZS = ["eu-west-3a", "eu-west-3b", "eu-west-3c"]
_INSTANCES = ["g4dn.xlarge", "p3.2xlarge", "p4d.24xlarge"]
_JOBS = ["fine-tune-llama-7b", "render-scene-042", "etl-batch-daily"]


def _random_price_event() -> dict:
    az = random.choice(_AZS)
    instance = random.choice(_INSTANCES)
    base = random.uniform(0.3, 4.5)
    delta = random.uniform(-0.15, 0.10)
    return {
        "type": "az_price_update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "az": az,
        "instance": instance,
        "old_price": round(base, 4),
        "new_price": round(base + delta, 4),
        "currency": "USD",
    }


def _random_checkpoint_event() -> dict:
    return {
        "type": "checkpoint_event",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": random.choice(_JOBS),
        "status": random.choice(["saving", "saved", "loading"]),
        "progress_pct": round(random.uniform(10, 95), 1),
        "checkpoint_size_gb": round(random.uniform(2.0, 14.0), 1),
    }


def _random_migration_event() -> dict:
    azs = random.sample(_AZS, 2)
    return {
        "type": "migration_complete",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": random.choice(_JOBS),
        "from_az": azs[0],
        "to_az": azs[1],
        "downtime_ms": 0,
        "reason": "Spot interruption — AZ-Hopping",
    }


def _random_timeshift_event() -> dict:
    return {
        "type": "timeshift_scheduled",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": random.choice(_JOBS),
        "scheduled_start": "2026-02-22T02:00:00Z",
        "estimated_savings_usd": round(random.uniform(5.0, 45.0), 2),
        "reason": "Prix Spot -35% entre 2h et 5h",
    }


_EVENT_GENERATORS = [
    (_random_price_event, 0.50),
    (_random_checkpoint_event, 0.20),
    (_random_migration_event, 0.15),
    (_random_timeshift_event, 0.15),
]


async def _demo_event_loop():
    """Boucle qui genere des events fictifs pour la demo."""
    while True:
        await asyncio.sleep(random.uniform(2.0, 5.0))
        # Choisir un type d'event selon les poids
        rand = random.random()
        cumulative = 0.0
        for generator, weight in _EVENT_GENERATORS:
            cumulative += weight
            if rand <= cumulative:
                event = generator()
                await broadcast(event)
                break


# ── WebSocket endpoint ───────────────────────────────────────────────

_demo_task: asyncio.Task | None = None


@router.websocket("/ws/feed")
async def websocket_feed(ws: WebSocket):
    """WebSocket pour le flux d'events temps reel."""
    global _demo_task
    await ws.accept()
    _connections.append(ws)

    # Lancer la boucle demo si pas deja active
    if _demo_task is None or _demo_task.done():
        _demo_task = asyncio.create_task(_demo_event_loop())

    # Message de bienvenue
    await ws.send_text(json.dumps({
        "type": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "NERVE WebSocket feed active",
        "active_clients": len(_connections),
    }))

    try:
        while True:
            # Garder la connexion ouverte, ecouter les pings
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _connections.remove(ws)
