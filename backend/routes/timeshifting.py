"""
POST /api/timeshifting/plan — Deadline → creneau optimal (nuit, heures creuses)
"""

from fastapi import APIRouter

from models import TimeShiftRequest, TimeShiftPlan
from engine.timeshifter import compute_timeshift_plan

router = APIRouter(prefix="/api", tags=["Time-Shifting"])


@router.post(
    "/timeshifting/plan",
    response_model=TimeShiftPlan,
    summary="Compute optimal time window for a job",
)
async def plan_timeshift(req: TimeShiftRequest):
    """
    Analyse les courbes de prix Spot + carbone sur 24h
    et recommande le meilleur creneau pour lancer le job.
    Respecte la deadline coute que coute.
    """
    return await compute_timeshift_plan(req)
