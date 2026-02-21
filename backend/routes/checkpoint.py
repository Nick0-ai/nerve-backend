"""
POST /api/checkpoint/simulate — Simule une interruption Spot + evacuation
"""

from fastapi import APIRouter

from models import CheckpointSimulateRequest, CheckpointEvent
from engine.checkpointing import simulate_interruption

router = APIRouter(prefix="/api", tags=["Checkpointing"])


@router.post(
    "/checkpoint/simulate",
    response_model=CheckpointEvent,
    summary="Simulate Spot interruption → checkpoint + migration",
)
async def checkpoint_simulate(req: CheckpointSimulateRequest):
    """
    Simule le protocole d'urgence NERVE :
    1. AWS envoie Spot Interruption Notice (2 min)
    2. NERVE ordonne la sauvegarde du checkpoint sur S3
    3. Cordon du noeud condamne
    4. Demarrage GPU Spot dans l'AZ voisine
    5. Reprise de l'entrainement exactement ou il s'est arrete
    """
    return await simulate_interruption(req)
