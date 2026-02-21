"""
GET /api/region   — Info de la region + ses 3 AZ
GET /api/azs      — Liste des AZ avec scores NERVE
"""

from fastapi import APIRouter, Query

from models import AZInfo, RegionInfo
from engine.scraper import get_region_data, get_all_azs

router = APIRouter(prefix="/api", tags=["Region & AZ"])


@router.get("/region", response_model=RegionInfo, summary="Region info + AZ overview")
async def get_region(
    region_id: str = Query("francecentral", example="francecentral"),
):
    """Retourne les infos de la region avec ses Availability Zones."""
    return await get_region_data(region_id)


@router.get("/azs", response_model=list[AZInfo], summary="All AZs with NERVE scores")
async def get_azs(
    region_id: str = Query("francecentral", example="francecentral"),
):
    """Retourne toutes les AZ de la region avec leur score NERVE (lower = better)."""
    return await get_all_azs(region_id)
