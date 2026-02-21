"""
GET /api/dashboard/stats — Stats agregees pour le dashboard
"""

from fastapi import APIRouter

from models import DashboardStats
from engine.scoring import get_dashboard_stats

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get(
    "/dashboard/stats",
    response_model=DashboardStats,
    summary="Aggregated FinOps/GreenOps stats",
)
async def dashboard_stats():
    """
    Retourne les stats agregees :
    - Total $ economies
    - Total CO2 evite
    - Nombre d'interruptions gerees
    - Nombre de checkpoints sauves
    """
    return await get_dashboard_stats()
