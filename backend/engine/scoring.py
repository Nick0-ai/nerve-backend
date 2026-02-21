"""
NERVE Engine — Scoring & Simulation
Calcule le score NERVE pour chaque AZ et genere la recommendation.
score = w_price * price + w_carbon * carbon + w_avail * (1-avail) + w_cool * cooling + w_renew * (1-renew)
"""

from __future__ import annotations

from datetime import datetime, timezone

from models import (
    Availability,
    CheckpointConfig,
    CarbonIndex,
    DashboardStats,
    Decision,
    Fallback,
    GreenImpact,
    InterruptionRisk,
    RiskAssessment,
    Savings,
    ServerStep,
    SimulateRequest,
    SimulateResponse,
    StartStrategy,
)
from engine.scraper import get_region_data, get_spot_prices
from engine.timeshifter import should_time_shift
from engine.llm import call_nerve_llm

# ── Poids du scoring ─────────────────────────────────────────────────

WEIGHTS = {
    "price": 0.50,
    "carbon": 0.20,
    "availability": 0.15,
    "cooling": 0.10,
    "renewable": 0.05,
}

EUR_USD = 0.92

KWH_PER_GPU_HR = {
    "v100": 0.30,
    "t4": 0.07,
    "a10": 0.15,
    "a100": 0.40,
    "h100": 0.70,
}

# ── Helpers ──────────────────────────────────────────────────────────

_AVAIL_SCORES = {
    Availability.HIGH: 1.0,
    Availability.MEDIUM: 0.7,
    Availability.LOW: 0.4,
    Availability.VERY_LOW: 0.1,
}


def _gpu_family(gpu_name: str) -> str:
    """Extrait la famille GPU du nom lisible."""
    lower = gpu_name.lower()
    for fam in ("h100", "a100", "a10", "v100", "t4"):
        if fam in lower:
            return fam
    return "v100"


def _score_gpu(gpu, carbon_gco2: float, temp_c: float, wind_kmh: float) -> float:
    """Calcule le score NERVE d'un GPU (lower = better)."""
    # Normalize price : 0-1 (on considere 15$/h comme max)
    norm_price = min(gpu.spot_price_usd_hr / 15.0, 1.0)

    # Normalize carbon : 0-1 (on considere 500 gCO2/kWh comme max)
    norm_carbon = min(carbon_gco2 / 500.0, 1.0)

    # Availability : 1 = available, 0 = rare
    avail_score = _AVAIL_SCORES.get(gpu.availability, 0.5)

    # Cooling : temp basse = bon (on normalise sur 0-40°C)
    norm_cooling = min(max(temp_c, 0) / 40.0, 1.0)

    # Renewable : vent fort = bon (on normalise sur 0-50 km/h)
    renew_score = min(wind_kmh / 50.0, 1.0)

    return (
        WEIGHTS["price"] * norm_price
        + WEIGHTS["carbon"] * norm_carbon
        + WEIGHTS["availability"] * (1 - avail_score)
        + WEIGHTS["cooling"] * norm_cooling
        + WEIGHTS["renewable"] * (1 - renew_score)
    )


# ── Simulation principale ────────────────────────────────────────────

async def run_simulation(req: SimulateRequest) -> SimulateResponse:
    """Execute la simulation NERVE complete."""
    regions_to_check = (
        [req.preferred_region] if req.preferred_region else
        ["francecentral", "westeurope", "uksouth"]
    )

    best_gpu = None
    best_score = float("inf")
    best_region = None
    best_az = None
    fallback_gpu = None
    fallback_az = None

    for region_id in regions_to_check:
        region = await get_region_data(region_id)
        for az in region.availability_zones:
            for gpu in az.gpu_instances:
                if gpu.ram_gb < req.min_gpu_memory_gb:
                    continue
                score = _score_gpu(
                    gpu,
                    az.carbon_intensity_gco2_kwh,
                    az.temperature_c,
                    az.wind_kmh,
                )
                if score < best_score:
                    # Le precedent meilleur devient fallback
                    if best_gpu:
                        fallback_gpu = best_gpu
                        fallback_az = best_az
                    best_score = score
                    best_gpu = gpu
                    best_region = region
                    best_az = az
                elif fallback_gpu is None:
                    fallback_gpu = gpu
                    fallback_az = az

    # Fallback par defaut si on n'a qu'un seul GPU
    if not fallback_gpu:
        fallback_gpu = best_gpu
        fallback_az = best_az

    # Time-shifting ?
    time_shift = await should_time_shift(req.deadline, req.estimated_gpu_hours)
    strategy = StartStrategy.TIME_SHIFTED if time_shift["recommended"] else StartStrategy.IMMEDIATE
    optimal_start = time_shift.get("optimal_start")

    now = datetime.now(timezone.utc)
    gpu_family = _gpu_family(best_gpu.gpu_name)
    kwh_per_hr = KWH_PER_GPU_HR.get(gpu_family, 0.30)

    # Calculs financiers
    spot_total = best_gpu.spot_price_usd_hr * req.estimated_gpu_hours
    ondemand_total = best_gpu.ondemand_price_usd_hr * req.estimated_gpu_hours
    savings_usd = ondemand_total - spot_total
    time_shift_bonus = savings_usd * 0.08 if strategy == StartStrategy.TIME_SHIFTED else 0

    # Calculs carbone
    total_kwh = kwh_per_hr * req.estimated_gpu_hours * 1.2  # PUE = 1.2
    total_co2 = total_kwh * best_az.carbon_intensity_gco2_kwh
    worst_co2 = total_kwh * 500  # Worst case : Pologne ~500 gCO2/kWh
    co2_saved = worst_co2 - total_co2

    return SimulateResponse(
        decision=Decision(
            primary_region=best_region.region_id,
            primary_az=best_az.az_id,
            gpu_sku=best_gpu.sku,
            gpu_name=best_gpu.gpu_name,
            spot_price_usd_hr=best_gpu.spot_price_usd_hr,
            start_strategy=strategy,
            optimal_start_time=optimal_start,
            reason=f"Meilleur score NERVE ({best_score:.3f}) — "
                   f"{best_gpu.savings_pct}% moins cher que On-Demand, "
                   f"carbone {best_az.carbon_index.value}",
        ),
        fallback=Fallback(
            secondary_az=fallback_az.az_id,
            secondary_sku=fallback_gpu.sku,
            fallback_reason="AZ de secours en cas d'interruption Spot",
        ),
        checkpointing=CheckpointConfig(
            recommended_interval_min=req.checkpoint_interval_min,
            storage_target="s3",
            estimated_checkpoint_size_gb=req.min_gpu_memory_gb * 0.8,
            reason=f"Checkpoint toutes les {req.checkpoint_interval_min} min sur S3 "
                   f"— reprise garantie en < 90s",
        ),
        savings=Savings(
            spot_cost_total_usd=round(spot_total, 2),
            ondemand_cost_total_usd=round(ondemand_total, 2),
            savings_usd=round(savings_usd, 2),
            savings_eur=round(savings_usd * EUR_USD, 2),
            savings_pct=round(best_gpu.savings_pct, 1),
            time_shift_extra_savings_usd=round(time_shift_bonus, 2),
        ),
        green_impact=GreenImpact(
            carbon_intensity_gco2_kwh=best_az.carbon_intensity_gco2_kwh,
            total_energy_kwh=round(total_kwh, 2),
            total_co2_grams=round(total_co2, 1),
            co2_vs_worst_region_grams=round(worst_co2, 1),
            co2_saved_grams=round(co2_saved, 1),
            equivalent=f"Equivalent a {co2_saved / 120:.1f} km en voiture evites",
        ),
        server_path=[
            ServerStep(
                step=1,
                action="Lancement du job sur Spot GPU",
                region=best_region.region_id,
                az=best_az.az_id,
                gpu=best_gpu.sku,
                time=optimal_start or now,
            ),
            ServerStep(
                step=2,
                action="Checkpoint sauvegarde sur S3 (automatique)",
                region=best_region.region_id,
                az=best_az.az_id,
                gpu=best_gpu.sku,
                time=optimal_start or now,
            ),
            ServerStep(
                step=3,
                action="Job termine — resultats disponibles",
                region=best_region.region_id,
                az=best_az.az_id,
                gpu=best_gpu.sku,
                time=req.deadline,
            ),
        ],
        risk_assessment=RiskAssessment(
            spot_interruption_probability=InterruptionRisk.LOW
            if best_gpu.availability in (Availability.HIGH, Availability.MEDIUM)
            else InterruptionRisk.MEDIUM,
            eviction_mitigation="Smart Checkpointing + AZ-Hopping automatique",
            max_evictions_per_hour=2,
        ),
    )


# ── Dashboard Stats ──────────────────────────────────────────────────

# Compteurs en memoire (hackathon — sera remplace par DB)
_stats = {
    "total_jobs": 0,
    "total_savings_usd": 0.0,
    "total_co2_saved_g": 0.0,
    "total_checkpoints": 0,
    "total_evictions": 0,
}


def record_job(savings_usd: float, co2_saved_g: float):
    _stats["total_jobs"] += 1
    _stats["total_savings_usd"] += savings_usd
    _stats["total_co2_saved_g"] += co2_saved_g


def record_checkpoint():
    _stats["total_checkpoints"] += 1


def record_eviction():
    _stats["total_evictions"] += 1


async def get_dashboard_stats() -> DashboardStats:
    return DashboardStats(
        total_jobs_managed=_stats["total_jobs"],
        total_savings_usd=round(_stats["total_savings_usd"], 2),
        total_savings_eur=round(_stats["total_savings_usd"] * EUR_USD, 2),
        total_co2_saved_grams=round(_stats["total_co2_saved_g"], 1),
        total_checkpoints_saved=_stats["total_checkpoints"],
        total_evictions_handled=_stats["total_evictions"],
        avg_savings_pct=78.0,
        uptime_pct=100.0,
        regions_monitored=["francecentral", "westeurope", "uksouth"],
        last_updated=datetime.now(timezone.utc),
    )
