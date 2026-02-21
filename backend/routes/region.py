"""
GET /api/region          — Info de la region + ses 3 AZ
GET /api/azs             — Liste des AZ avec scores NERVE
GET /api/regions/summary — Resume live de toutes les regions (pour dashboard)
GET /api/prices/curve    — Courbe de prix Spot 24h live
"""

from fastapi import APIRouter, Query

from models import AZInfo, RegionInfo
from engine.scraper import get_region_data, get_all_azs, get_cache, REGIONS

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


@router.get("/regions/summary", summary="Live summary of all regions for dashboard")
async def regions_summary():
    """Return live region data: cheapest GPU, carbon, weather for each region."""
    cache = get_cache()
    result = []
    for region_id, cfg in REGIONS.items():
        gpus = cache.get("gpu_prices", {}).get(region_id, [])
        carbon = cache.get("carbon", {}).get(region_id, {})
        weather = cache.get("weather", {}).get(region_id, {})

        cheapest = None
        if gpus:
            cheapest = min(gpus, key=lambda g: g["spot_price_usd_hr"])

        result.append({
            "region_id": region_id,
            "region_name": cfg["name"],
            "location": cfg["location"],
            "carbon_gco2_kwh": carbon.get("gco2_kwh", 0),
            "carbon_index": carbon.get("index", "unknown"),
            "carbon_source": carbon.get("source", ""),
            "temperature_c": weather.get("current_temp_c", 0),
            "wind_kmh": weather.get("current_wind_kmh", 0),
            "gpu_count": len(gpus),
            "cheapest_gpu_name": cheapest["gpu_name"] if cheapest else "N/A",
            "cheapest_spot_price": cheapest["spot_price_usd_hr"] if cheapest else 0,
            "cheapest_ondemand_price": cheapest["ondemand_price_usd_hr"] if cheapest else 0,
            "cheapest_savings_pct": cheapest["savings_pct"] if cheapest else 0,
            "cheapest_sku": cheapest["sku"] if cheapest else "N/A",
        })
    return result


@router.get("/prices/curve", summary="Live 24h spot price curve for a region")
async def price_curve(
    region_id: str = Query("francecentral", example="francecentral"),
):
    """
    24h spot price curve. Uses REAL price history when available.
    Falls back to model-based curve from live average price.
    """
    from engine.scraper import get_price_history
    from engine.timeshifter import _build_live_price_curve

    cache = get_cache()
    gpus = cache.get("gpu_prices", {}).get(region_id, [])

    compute_gpus = [g for g in gpus if g["sku"].startswith("Standard_NC") or g["sku"].startswith("Standard_ND")]
    if not compute_gpus:
        compute_gpus = gpus
    cheapest = min(compute_gpus, key=lambda g: g["spot_price_usd_hr"]) if compute_gpus else None
    ondemand = cheapest["ondemand_price_usd_hr"] if cheapest else 3.58

    history = get_price_history(region_id)
    model_curve = _build_live_price_curve(region_id)

    if len(history) >= 3:
        hour_data: dict[int, list[float]] = {}
        for entry in history:
            h = entry.get("hour", 0)
            if h not in hour_data:
                hour_data[h] = []
            hour_data[h].append(entry["avg_compute_spot"])

        data = []
        for h in range(24):
            if h in hour_data:
                spot = round(sum(hour_data[h]) / len(hour_data[h]), 4)
                data.append({"hour": f"{h:02d}h", "spot": spot, "ondemand": round(ondemand, 4), "source": "scraped"})
            else:
                data.append({"hour": f"{h:02d}h", "spot": round(model_curve.get(h, 0.5), 4), "ondemand": round(ondemand, 4), "source": "model"})

        scraped_count = sum(1 for d in data if d["source"] == "scraped")
        source = f"history ({scraped_count}/24h real)"
    else:
        data = [
            {"hour": f"{h:02d}h", "spot": round(model_curve.get(h, 0.5), 4), "ondemand": round(ondemand, 4), "source": "model"}
            for h in range(24)
        ]
        source = f"model (building history: {len(history)} points)"

    return {
        "region_id": region_id,
        "gpu_name": cheapest["gpu_name"] if cheapest else "N/A",
        "sku": cheapest["sku"] if cheapest else "N/A",
        "source": source,
        "history_points": len(history),
        "data": data,
    }
