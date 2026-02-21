"""
NERVE — API Backend (LIVE)
All data scraped in real-time from Azure, Open-Meteo, Carbon Intensity UK.

Usage:
    cp .env.example .env  # configure LLM API key
    uvicorn main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
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
from engine.scraper import start_scraper, stop_scraper, get_scraper_status

# Load .env for LLM API keys
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch live scraper
    await start_scraper()
    logging.info("NERVE engine started — live scraper running")
    yield
    # Shutdown
    await stop_scraper()
    logging.info("NERVE engine stopped")


app = FastAPI(
    title="NERVE API (LIVE)",
    description=(
        "Cloud FinOps/GreenOps Orchestrator — "
        "All data scraped in real-time from Azure, Open-Meteo, Carbon Intensity UK."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(region_router)
app.include_router(simulate_router)
app.include_router(checkpoint_router)
app.include_router(timeshifting_router)
app.include_router(dashboard_router)
app.include_router(ws_router)


@app.get("/health", tags=["System"])
async def health():
    status = get_scraper_status()
    return {
        "status": "ok",
        "engine": "NERVE v2.0.0 (LIVE)",
        "scraper": status,
    }
