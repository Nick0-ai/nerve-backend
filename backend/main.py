"""
NERVE — API Backend
FastAPI server pour l'orchestrateur FinOps/GreenOps.

Usage:
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import (
    region_router,
    simulate_router,
    checkpoint_router,
    timeshifting_router,
    dashboard_router,
)
from ws import ws_router


# ── Lifespan (startup / shutdown) ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : precharger les donnees
    from engine.scraper import _ensure_cache
    _ensure_cache()
    print("NERVE engine started — cache loaded")
    yield
    # Shutdown
    print("NERVE engine stopped")


# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="NERVE API",
    description=(
        "Orchestrateur Cloud FinOps/GreenOps — "
        "AZ-Hopping, Time-Shifting, Smart Checkpointing"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (William peut fetch depuis localhost:8080) ──────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────

app.include_router(region_router)
app.include_router(simulate_router)
app.include_router(checkpoint_router)
app.include_router(timeshifting_router)
app.include_router(dashboard_router)
app.include_router(ws_router)


# ── Health check ─────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "engine": "NERVE v1.0.0"}
