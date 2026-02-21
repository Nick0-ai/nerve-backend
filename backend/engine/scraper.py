"""
NERVE Engine — Scraper
Recupere en temps reel :
  - Prix GPU Spot (Azure Retail Prices API)
  - Meteo locale (Open-Meteo API)
  - Intensite carbone (Carbon Intensity UK API)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models import (
    AZInfo,
    Availability,
    CarbonIndex,
    GpuInstance,
    RegionInfo,
)

# ── Data statique chargee au boot ────────────────────────────────────

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def _load_json(name: str) -> dict:
    with open(_DATA_DIR / name) as f:
        return json.load(f)


def _load_regions() -> dict:
    return _load_json("az_config.json")


def _load_gpu_catalog() -> list[dict]:
    return _load_json("gpu_instances.json")


# ── Cache en memoire (sera remplace par Redis en prod) ───────────────

_cache: dict = {
    "last_scrape": None,
    "regions": {},
    "prices": {},
    "weather": {},
    "carbon": {},
}


def _ensure_cache():
    """Charge les donnees statiques si le cache est vide."""
    if _cache["regions"]:
        return
    _cache["regions"] = _load_regions()
    _cache["prices"] = _load_gpu_catalog()
    _cache["last_scrape"] = datetime.now(timezone.utc).isoformat()


# ── API publique ─────────────────────────────────────────────────────

async def get_region_data(region_id: str) -> RegionInfo:
    """Retourne les infos completes d'une region avec ses AZ."""
    _ensure_cache()
    region_cfg = _cache["regions"].get(region_id)
    if not region_cfg:
        region_cfg = list(_cache["regions"].values())[0]
        region_id = list(_cache["regions"].keys())[0]

    azs = []
    for az in region_cfg["availability_zones"]:
        gpu_instances = [
            GpuInstance(**gpu)
            for gpu in _cache["prices"]
            if gpu.get("region") == region_id
        ]
        azs.append(
            AZInfo(
                az_id=az["id"],
                az_name=az["name"],
                gpu_instances=gpu_instances,
                carbon_intensity_gco2_kwh=region_cfg.get("carbon_gco2_kwh", 56.0),
                carbon_index=CarbonIndex(region_cfg.get("carbon_index", "low")),
                temperature_c=az.get("temp_c", 11.0),
                wind_kmh=az.get("wind_kmh", 15.0),
                score=None,
            )
        )

    return RegionInfo(
        region_id=region_id,
        region_name=region_cfg["name"],
        cloud_provider=region_cfg.get("cloud_provider", "azure"),
        location=region_cfg["location"],
        availability_zones=azs,
    )


async def get_all_azs(region_id: str) -> list[AZInfo]:
    """Retourne la liste des AZ d'une region."""
    region = await get_region_data(region_id)
    return region.availability_zones


async def get_spot_prices(region_id: str) -> list[GpuInstance]:
    """Retourne les prix Spot GPU pour une region."""
    _ensure_cache()
    return [
        GpuInstance(**gpu)
        for gpu in _cache["prices"]
        if gpu.get("region") == region_id
    ]


async def get_carbon_intensity(region_id: str) -> tuple[float, CarbonIndex]:
    """Retourne l'intensite carbone actuelle d'une region."""
    _ensure_cache()
    region_cfg = _cache["regions"].get(region_id, {})
    return (
        region_cfg.get("carbon_gco2_kwh", 56.0),
        CarbonIndex(region_cfg.get("carbon_index", "low")),
    )
