"""
POST /api/simulate — Soumet un job, NERVE retourne le meilleur choix serveur + savings
"""

from fastapi import APIRouter

from models import SimulateRequest, SimulateResponse
from engine.scoring import run_simulation

router = APIRouter(prefix="/api", tags=["Simulation"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="Simulate job placement → best AZ + savings",
)
async def simulate_job(req: SimulateRequest):
    """
    Le coeur de NERVE.
    Recoit un job (type, deadline, GPU requis) et retourne :
    - La decision (region, AZ, GPU, strategie)
    - Le fallback
    - La config de checkpointing
    - Les economies en USD/EUR
    - L'impact carbone
    - Le chemin serveur complet
    """
    return await run_simulation(req)
