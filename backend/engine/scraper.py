"""
NERVE Engine — Live Scraper
Scrape en temps reel (boucle async toutes les 60s) :
  - Azure Retail Prices API (GPU Spot prices, 3 regions)
  - Open-Meteo API (meteo Paris, Amsterdam, Londres)
  - Carbon Intensity UK API (gCO2/kWh reel)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from models import (
    AZInfo,
    Availability,
    CarbonIndex,
    GpuInstance,
    RegionInfo,
)

log = logging.getLogger("nerve.scraper")

# ── Config regions ───────────────────────────────────────────────────

REGIONS = {
    "francecentral": {
        "name": "France Central",
        "cloud_provider": "azure",
        "location": "Paris, France",
        "lat": 48.8566,
        "lng": 2.3522,
        "timezone": "Europe/Paris",
        "azs": [
            {"id": "fr-central-1", "name": "France Central AZ-1"},
            {"id": "fr-central-2", "name": "France Central AZ-2"},
            {"id": "fr-central-3", "name": "France Central AZ-3"},
        ],
    },
    "westeurope": {
        "name": "West Europe",
        "cloud_provider": "azure",
        "location": "Amsterdam, Netherlands",
        "lat": 52.3676,
        "lng": 4.9041,
        "timezone": "Europe/Amsterdam",
        "azs": [
            {"id": "we-1", "name": "West Europe AZ-1"},
            {"id": "we-2", "name": "West Europe AZ-2"},
            {"id": "we-3", "name": "West Europe AZ-3"},
        ],
    },
    "uksouth": {
        "name": "UK South",
        "cloud_provider": "azure",
        "location": "London, UK",
        "lat": 51.5074,
        "lng": -0.1278,
        "timezone": "Europe/London",
        "azs": [
            {"id": "uk-south-1", "name": "UK South AZ-1"},
            {"id": "uk-south-2", "name": "UK South AZ-2"},
            {"id": "uk-south-3", "name": "UK South AZ-3"},
        ],
    },
}

# GPU families we care about (NC = compute GPU, NV = visualization GPU)
GPU_SKU_PREFIXES = ("Standard_NC", "Standard_NV", "Standard_ND")

# ── Live cache ───────────────────────────────────────────────────────

_cache: dict[str, Any] = {
    "last_scrape": None,
    "gpu_prices": {},      # region_id -> list[dict]
    "weather": {},         # region_id -> dict
    "carbon": {},          # region_id -> dict
    "scrape_count": 0,
    "errors": [],
}

_event_listeners: list[Callable] = []

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def on_event(fn: Callable):
    """Register a listener for scraper events (used by WebSocket)."""
    _event_listeners.append(fn)


def _emit(event: dict):
    """Emit an event to all registered listeners."""
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    for fn in _event_listeners:
        try:
            fn(event)
        except Exception:
            pass


# ── Azure Retail Prices API ──────────────────────────────────────────

async def _scrape_azure_gpu_prices(client: httpx.AsyncClient, region_id: str) -> list[dict]:
    """Fetch real GPU Spot prices from Azure Retail Prices API."""
    gpus: list[dict] = []

    for prefix_type in ["NC", "NV", "ND"]:
        url = (
            "https://prices.azure.com/api/retail/prices"
            f"?$filter=serviceName eq 'Virtual Machines'"
            f" and armRegionName eq '{region_id}'"
            f" and contains(meterName,'Spot')"
            f" and contains(armSkuName,'{prefix_type}')"
        )
        try:
            resp = await client.get(url, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("Items", [])

            # Deduplicate: keep cheapest per SKU (Windows vs Linux)
            seen: dict[str, dict] = {}
            for item in items:
                sku = item.get("armSkuName", "")
                price = item.get("retailPrice", 999)
                if sku not in seen or price < seen[sku]["retailPrice"]:
                    seen[sku] = item

            for sku, item in seen.items():
                gpu_info = _identify_gpu(sku)
                if not gpu_info:
                    continue
                gpus.append({
                    "region": region_id,
                    "sku": sku,
                    "gpu_name": gpu_info["name"],
                    "gpu_count": gpu_info["count"],
                    "vcpus": gpu_info["vcpus"],
                    "ram_gb": gpu_info["ram_gb"],
                    "spot_price_usd_hr": round(item["retailPrice"], 6),
                    "ondemand_price_usd_hr": 0.0,  # fetched separately
                    "savings_pct": 0.0,
                    "availability": _estimate_availability(item["retailPrice"], gpu_info["tier"]),
                })

            log.info(f"Azure {region_id}/{prefix_type}: {len(seen)} GPU SKUs")
        except Exception as e:
            log.warning(f"Azure scrape failed {region_id}/{prefix_type}: {e}")
            _cache["errors"].append(f"Azure {region_id}/{prefix_type}: {e}")

    # Fetch on-demand prices for savings calculation
    await _enrich_ondemand_prices(client, region_id, gpus)

    return gpus


async def _enrich_ondemand_prices(client: httpx.AsyncClient, region_id: str, gpus: list[dict]):
    """Fetch on-demand prices for each GPU SKU to compute savings %."""
    for gpu in gpus:
        sku = gpu["sku"]
        url = (
            "https://prices.azure.com/api/retail/prices"
            f"?$filter=serviceName eq 'Virtual Machines'"
            f" and armRegionName eq '{region_id}'"
            f" and armSkuName eq '{sku}'"
        )
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            items = resp.json().get("Items", [])
            # Find the non-Spot, non-Low Priority price
            for item in items:
                meter = item.get("meterName", "")
                if "Spot" not in meter and "Low Priority" not in meter:
                    od_price = item["retailPrice"]
                    gpu["ondemand_price_usd_hr"] = round(od_price, 4)
                    if od_price > 0:
                        gpu["savings_pct"] = round((1 - gpu["spot_price_usd_hr"] / od_price) * 100, 1)
                    break
        except Exception:
            # Estimate on-demand as ~5x spot if API fails
            gpu["ondemand_price_usd_hr"] = round(gpu["spot_price_usd_hr"] * 5, 4)
            gpu["savings_pct"] = 80.0


def _identify_gpu(sku: str) -> dict | None:
    """Map Azure SKU name to GPU specs."""
    s = sku.lower()
    catalog = {
        "nc6s_v3":    {"name": "Tesla V100 (16GB)", "count": 1, "vcpus": 6, "ram_gb": 112, "tier": "high"},
        "nc12s_v3":   {"name": "Tesla V100 (16GB)", "count": 2, "vcpus": 12, "ram_gb": 224, "tier": "high"},
        "nc24s_v3":   {"name": "Tesla V100 (16GB)", "count": 4, "vcpus": 24, "ram_gb": 448, "tier": "high"},
        "nc24rs_v3":  {"name": "Tesla V100 (16GB)", "count": 4, "vcpus": 24, "ram_gb": 448, "tier": "high"},
        "nc4as_t4_v3":  {"name": "Tesla T4 (16GB)", "count": 1, "vcpus": 4, "ram_gb": 28, "tier": "mid"},
        "nc8as_t4_v3":  {"name": "Tesla T4 (16GB)", "count": 1, "vcpus": 8, "ram_gb": 56, "tier": "mid"},
        "nc16as_t4_v3": {"name": "Tesla T4 (16GB)", "count": 1, "vcpus": 16, "ram_gb": 110, "tier": "mid"},
        "nc64as_t4_v3": {"name": "Tesla T4 (16GB)", "count": 4, "vcpus": 64, "ram_gb": 440, "tier": "mid"},
        "nc8ads_a10_v4":  {"name": "A10 (24GB)", "count": 1, "vcpus": 8, "ram_gb": 55, "tier": "mid"},
        "nc16ads_a10_v4": {"name": "A10 (24GB)", "count": 1, "vcpus": 16, "ram_gb": 110, "tier": "mid"},
        "nc32ads_a10_v4": {"name": "A10 (24GB)", "count": 2, "vcpus": 32, "ram_gb": 220, "tier": "mid"},
        "nc48ads_a100_v4": {"name": "A100 (80GB)", "count": 2, "vcpus": 48, "ram_gb": 440, "tier": "premium"},
        "nc96ads_a100_v4": {"name": "A100 (80GB)", "count": 4, "vcpus": 96, "ram_gb": 880, "tier": "premium"},
        "ncc40ads_h100_v5": {"name": "H100 (80GB)", "count": 1, "vcpus": 40, "ram_gb": 320, "tier": "premium"},
        "nc80adis_h100_v5": {"name": "H100 (80GB)", "count": 2, "vcpus": 80, "ram_gb": 640, "tier": "premium"},
        "nv6ads_a10_v5":  {"name": "A10 (6GB slice)", "count": 1, "vcpus": 6, "ram_gb": 55, "tier": "low"},
        "nv12ads_a10_v5": {"name": "A10 (12GB slice)", "count": 1, "vcpus": 12, "ram_gb": 110, "tier": "low"},
        "nv18ads_a10_v5": {"name": "A10 (18GB slice)", "count": 1, "vcpus": 18, "ram_gb": 220, "tier": "mid"},
        "nv36ads_a10_v5": {"name": "A10 (24GB)", "count": 1, "vcpus": 36, "ram_gb": 440, "tier": "mid"},
        "nv4as_v4":   {"name": "Radeon MI25 (4GB)", "count": 1, "vcpus": 4, "ram_gb": 14, "tier": "low"},
        "nv8as_v4":   {"name": "Radeon MI25 (8GB)", "count": 1, "vcpus": 8, "ram_gb": 28, "tier": "low"},
        "nv16as_v4":  {"name": "Radeon MI25 (16GB)", "count": 1, "vcpus": 16, "ram_gb": 56, "tier": "low"},
        "nv32as_v4":  {"name": "Radeon MI25 (32GB)", "count": 1, "vcpus": 32, "ram_gb": 112, "tier": "low"},
        "nv12s_v3":   {"name": "Tesla M60 (8GB)", "count": 1, "vcpus": 12, "ram_gb": 112, "tier": "low"},
        "nv24s_v3":   {"name": "Tesla M60 (16GB)", "count": 2, "vcpus": 24, "ram_gb": 224, "tier": "low"},
        "nv48s_v3":   {"name": "Tesla M60 (32GB)", "count": 4, "vcpus": 48, "ram_gb": 448, "tier": "low"},
    }
    for key, specs in catalog.items():
        if key in s:
            return specs
    return None


def _estimate_availability(price: float, tier: str) -> str:
    """Estimate Spot availability based on price tier."""
    if tier == "premium":
        return "low"
    if tier == "high":
        return "medium" if price > 2.0 else "high"
    if tier == "mid":
        return "high"
    return "high"


# ── Open-Meteo API ───────────────────────────────────────────────────

async def _scrape_weather(client: httpx.AsyncClient, region_id: str) -> dict:
    """Fetch real weather data from Open-Meteo."""
    cfg = REGIONS[region_id]
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={cfg['lat']}&longitude={cfg['lng']}"
        f"&hourly=temperature_2m,windspeed_10m,direct_radiation"
        f"&timezone={cfg['timezone']}&forecast_days=1"
    )
    try:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        hourly = data.get("hourly", {})
        temps = hourly.get("temperature_2m", [])
        winds = hourly.get("windspeed_10m", [])
        solar = hourly.get("direct_radiation", [])
        hours = hourly.get("time", [])

        now_hour = datetime.now(timezone.utc).hour
        current_temp = temps[now_hour] if now_hour < len(temps) else temps[0] if temps else 10.0
        current_wind = winds[now_hour] if now_hour < len(winds) else winds[0] if winds else 15.0
        current_solar = solar[now_hour] if now_hour < len(solar) else 0.0

        result = {
            "current_temp_c": current_temp,
            "current_wind_kmh": current_wind,
            "current_solar_wm2": current_solar,
            "hourly": [
                {
                    "hour": hours[i] if i < len(hours) else f"{i:02d}:00",
                    "temp_c": temps[i] if i < len(temps) else 10.0,
                    "wind_kmh": winds[i] if i < len(winds) else 15.0,
                    "solar_wm2": solar[i] if i < len(solar) else 0.0,
                }
                for i in range(min(24, len(temps)))
            ],
        }
        log.info(f"Weather {region_id}: {current_temp}°C, {current_wind} km/h wind")
        return result
    except Exception as e:
        log.warning(f"Weather scrape failed {region_id}: {e}")
        _cache["errors"].append(f"Weather {region_id}: {e}")
        return {"current_temp_c": 10.0, "current_wind_kmh": 15.0, "current_solar_wm2": 0.0, "hourly": []}


# ── Carbon Intensity API ─────────────────────────────────────────────

CARBON_DEFAULTS = {
    "francecentral": {"gco2_kwh": 56.0, "index": "low", "source": "RTE (nuclear-dominated grid)"},
    "westeurope": {"gco2_kwh": 328.0, "index": "moderate", "source": "NL gas-dominated grid"},
    "uksouth": {"gco2_kwh": 120.0, "index": "low", "source": "Carbon Intensity UK API"},
}


async def _scrape_carbon(client: httpx.AsyncClient, region_id: str) -> dict:
    """Fetch real carbon intensity. UK has a real API, others use known grid averages."""
    if region_id == "uksouth":
        try:
            resp = await client.get(
                "https://api.carbonintensity.org.uk/intensity",
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            entry = data.get("data", [{}])[0]
            intensity = entry.get("intensity", {})
            actual = intensity.get("actual") or intensity.get("forecast", 120)
            index_val = intensity.get("index", "low")
            log.info(f"Carbon UK: {actual} gCO2/kWh ({index_val})")
            return {
                "gco2_kwh": actual,
                "index": index_val,
                "source": "carbonintensity.org.uk (LIVE)",
                "from": entry.get("from"),
                "to": entry.get("to"),
            }
        except Exception as e:
            log.warning(f"Carbon UK scrape failed: {e}")
            _cache["errors"].append(f"Carbon UK: {e}")

    # France: use RTE known average (API requires auth token)
    # Netherlands: use known average
    default = CARBON_DEFAULTS.get(region_id, CARBON_DEFAULTS["francecentral"])
    return {
        "gco2_kwh": default["gco2_kwh"],
        "index": default["index"],
        "source": default["source"],
    }


# ── Main scrape loop ─────────────────────────────────────────────────

_scraper_task: asyncio.Task | None = None
SCRAPE_INTERVAL = 60  # seconds


async def _scrape_all():
    """Single scrape cycle — fetch all data sources."""
    _cache["errors"] = []
    async with httpx.AsyncClient() as client:
        for region_id in REGIONS:
            # Scrape in parallel per region
            gpu_task = _scrape_azure_gpu_prices(client, region_id)
            weather_task = _scrape_weather(client, region_id)
            carbon_task = _scrape_carbon(client, region_id)

            gpus, weather, carbon = await asyncio.gather(
                gpu_task, weather_task, carbon_task
            )

            old_prices = _cache["gpu_prices"].get(region_id, [])
            _cache["gpu_prices"][region_id] = gpus
            _cache["weather"][region_id] = weather
            _cache["carbon"][region_id] = carbon

            # Emit price change events
            _detect_price_changes(region_id, old_prices, gpus)

    _cache["last_scrape"] = datetime.now(timezone.utc).isoformat()
    _cache["scrape_count"] += 1
    total_gpus = sum(len(v) for v in _cache["gpu_prices"].values())
    log.info(f"Scrape #{_cache['scrape_count']} complete — {total_gpus} GPUs across {len(REGIONS)} regions")


def _detect_price_changes(region_id: str, old: list[dict], new: list[dict]):
    """Detect price changes and emit WS events."""
    old_map = {g["sku"]: g["spot_price_usd_hr"] for g in old}
    for gpu in new:
        old_price = old_map.get(gpu["sku"])
        if old_price is not None and old_price != gpu["spot_price_usd_hr"]:
            _emit({
                "type": "az_price_update",
                "region": region_id,
                "az": REGIONS[region_id]["azs"][0]["id"],
                "instance": gpu["sku"],
                "gpu_name": gpu["gpu_name"],
                "old_price": old_price,
                "new_price": gpu["spot_price_usd_hr"],
                "currency": "USD",
            })


async def _scrape_loop():
    """Background loop that scrapes every SCRAPE_INTERVAL seconds."""
    while True:
        try:
            await _scrape_all()
        except Exception as e:
            log.error(f"Scrape loop error: {e}")
        await asyncio.sleep(SCRAPE_INTERVAL)


async def start_scraper():
    """Start the background scraper. Call from FastAPI lifespan."""
    global _scraper_task
    log.info("Starting NERVE live scraper...")
    # First scrape immediately
    await _scrape_all()
    # Then loop
    _scraper_task = asyncio.create_task(_scrape_loop())


async def stop_scraper():
    """Stop the background scraper."""
    global _scraper_task
    if _scraper_task:
        _scraper_task.cancel()
        _scraper_task = None
    log.info("NERVE scraper stopped")


# ── Public API (used by routes + scoring) ────────────────────────────

def get_cache() -> dict:
    """Return the full live cache (for LLM context)."""
    return _cache


async def get_region_data(region_id: str) -> RegionInfo:
    """Build RegionInfo from live scraped data."""
    if region_id not in REGIONS:
        region_id = "francecentral"

    cfg = REGIONS[region_id]
    weather = _cache.get("weather", {}).get(region_id, {})
    carbon = _cache.get("carbon", {}).get(region_id, {})
    gpus_raw = _cache.get("gpu_prices", {}).get(region_id, [])

    gpu_instances = [
        GpuInstance(
            sku=g["sku"],
            gpu_name=g["gpu_name"],
            gpu_count=g["gpu_count"],
            vcpus=g["vcpus"],
            ram_gb=g["ram_gb"],
            spot_price_usd_hr=g["spot_price_usd_hr"],
            ondemand_price_usd_hr=g["ondemand_price_usd_hr"],
            savings_pct=g["savings_pct"],
            availability=Availability(g["availability"]),
        )
        for g in gpus_raw
    ]

    # Build AZ list with weather data distributed
    azs = []
    for i, az_cfg in enumerate(cfg["azs"]):
        hourly = weather.get("hourly", [])
        temp = weather.get("current_temp_c", 10.0) + (i * 0.2 - 0.2)  # slight AZ variation
        wind = weather.get("current_wind_kmh", 15.0) + (i * 0.5 - 0.5)
        gco2 = carbon.get("gco2_kwh", 56.0)
        idx = carbon.get("index", "low")

        azs.append(AZInfo(
            az_id=az_cfg["id"],
            az_name=az_cfg["name"],
            gpu_instances=gpu_instances,
            carbon_intensity_gco2_kwh=gco2,
            carbon_index=CarbonIndex(idx),
            temperature_c=round(temp, 1),
            wind_kmh=round(wind, 1),
            score=None,
        ))

    return RegionInfo(
        region_id=region_id,
        region_name=cfg["name"],
        cloud_provider=cfg["cloud_provider"],
        location=cfg["location"],
        availability_zones=azs,
    )


async def get_all_azs(region_id: str) -> list[AZInfo]:
    region = await get_region_data(region_id)
    return region.availability_zones


async def get_spot_prices(region_id: str) -> list[GpuInstance]:
    region = await get_region_data(region_id)
    if region.availability_zones:
        return region.availability_zones[0].gpu_instances
    return []


async def get_carbon_intensity(region_id: str) -> tuple[float, CarbonIndex]:
    carbon = _cache.get("carbon", {}).get(region_id, {})
    return (
        carbon.get("gco2_kwh", 56.0),
        CarbonIndex(carbon.get("index", "low")),
    )


def get_live_weather(region_id: str) -> dict:
    """Return live hourly weather for time-shifter."""
    return _cache.get("weather", {}).get(region_id, {})


def get_scraper_status() -> dict:
    return {
        "last_scrape": _cache["last_scrape"],
        "scrape_count": _cache["scrape_count"],
        "total_gpus": sum(len(v) for v in _cache["gpu_prices"].values()),
        "regions": list(_cache["gpu_prices"].keys()),
        "errors": _cache["errors"][-10:],
    }
