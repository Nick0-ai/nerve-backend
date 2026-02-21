"""
NERVE Engine — Time-Shifter
Analyse les creux tarifaires et propose le meilleur creneau.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from models import TimeShiftPlan, TimeShiftRequest

# ── Prix Spot typiques par heure (normalises 0-1, basé sur données reelles)
# 0.0 = prix plancher (2h-5h), 1.0 = prix peak (10h-14h)

PRICE_CURVE_24H = {
    0: 0.25, 1: 0.18, 2: 0.10, 3: 0.08, 4: 0.10, 5: 0.15,
    6: 0.30, 7: 0.50, 8: 0.65, 9: 0.80, 10: 0.95, 11: 1.00,
    12: 0.98, 13: 0.95, 14: 0.90, 15: 0.82, 16: 0.75, 17: 0.70,
    18: 0.60, 19: 0.50, 20: 0.42, 21: 0.35, 22: 0.30, 23: 0.28,
}

# Intensite carbone relative (France - normalise, nuclear = baseline)
CARBON_CURVE_24H = {
    0: 0.30, 1: 0.25, 2: 0.20, 3: 0.18, 4: 0.20, 5: 0.25,
    6: 0.35, 7: 0.50, 8: 0.60, 9: 0.70, 10: 0.75, 11: 0.80,
    12: 0.85, 13: 0.80, 14: 0.75, 15: 0.70, 16: 0.65, 17: 0.70,
    18: 0.80, 19: 0.85, 20: 0.75, 21: 0.60, 22: 0.45, 23: 0.35,
}


def _find_optimal_window(
    hours_needed: float,
    deadline: datetime,
) -> tuple[Optional[datetime], Optional[datetime], float, float]:
    """Trouve le creneau optimal avant la deadline."""
    now = datetime.now(timezone.utc)
    hours_int = int(hours_needed) + 1  # Marge de securite

    # Combien d'heures avant la deadline ?
    hours_until_deadline = (deadline - now).total_seconds() / 3600
    if hours_until_deadline < hours_needed:
        return None, None, 0.0, 0.0

    best_start_hour = None
    best_cost = float("inf")

    # Tester chaque heure de depart possible
    for start_offset_h in range(int(hours_until_deadline - hours_needed) + 1):
        candidate_start = now + timedelta(hours=start_offset_h)
        total_cost = 0.0
        for h in range(hours_int):
            run_hour = (candidate_start.hour + h) % 24
            total_cost += PRICE_CURVE_24H.get(run_hour, 0.5)

        if total_cost < best_cost:
            best_cost = total_cost
            best_start_hour = start_offset_h

    if best_start_hour is None:
        return None, None, 0.0, 0.0

    optimal_start = now + timedelta(hours=best_start_hour)
    optimal_end = optimal_start + timedelta(hours=hours_needed)

    # Calcul de la reduction de prix vs maintenant
    current_cost = sum(
        PRICE_CURVE_24H.get((now.hour + h) % 24, 0.5)
        for h in range(hours_int)
    )
    price_reduction = ((current_cost - best_cost) / current_cost * 100) if current_cost > 0 else 0

    # Calcul de la reduction carbone
    current_carbon = sum(
        CARBON_CURVE_24H.get((now.hour + h) % 24, 0.5)
        for h in range(hours_int)
    )
    optimal_carbon = sum(
        CARBON_CURVE_24H.get((optimal_start.hour + h) % 24, 0.5)
        for h in range(hours_int)
    )
    carbon_reduction = (
        (current_carbon - optimal_carbon) / current_carbon * 100
    ) if current_carbon > 0 else 0

    return optimal_start, optimal_end, max(price_reduction, 0), max(carbon_reduction, 0)


async def should_time_shift(
    deadline: datetime,
    gpu_hours: float,
) -> dict:
    """Determine si le time-shifting est recommande."""
    start, end, price_red, carbon_red = _find_optimal_window(gpu_hours, deadline)

    if start and price_red > 10:
        return {
            "recommended": True,
            "optimal_start": start,
            "optimal_end": end,
            "price_reduction_pct": price_red,
            "carbon_reduction_pct": carbon_red,
        }
    return {"recommended": False, "optimal_start": None}


async def compute_timeshift_plan(req: TimeShiftRequest) -> TimeShiftPlan:
    """Calcule le plan de time-shifting complet."""
    now = datetime.now(timezone.utc)
    current_hour = now.hour

    start, end, price_red, carbon_red = _find_optimal_window(
        req.estimated_gpu_hours, req.deadline
    )

    recommended = start is not None and price_red > 10 and req.flexible
    meets_deadline = True
    if end and end > req.deadline:
        recommended = False
        meets_deadline = False

    # Prix Spot estimes
    current_price_factor = PRICE_CURVE_24H.get(current_hour, 0.5)
    optimal_price_factor = (
        PRICE_CURVE_24H.get(start.hour, 0.5) if start else current_price_factor
    )

    # Prix de reference : NC6s_v3 Spot francecentral
    base_spot = 0.6616
    current_price = base_spot * (0.5 + current_price_factor)
    optimal_price = base_spot * (0.5 + optimal_price_factor)

    return TimeShiftPlan(
        recommended=recommended,
        optimal_window_start=start,
        optimal_window_end=end,
        reason=(
            f"Decaler le job a {start.strftime('%Hh%M') if start else 'N/A'} "
            f"reduit le cout de {price_red:.0f}% et le carbone de {carbon_red:.0f}%"
            if recommended
            else "Le creneau actuel est optimal ou la deadline ne permet pas de decaler"
        ),
        estimated_spot_price_usd_hr=round(optimal_price, 4),
        current_spot_price_usd_hr=round(current_price, 4),
        price_reduction_pct=round(price_red, 1),
        carbon_reduction_pct=round(carbon_red, 1),
        meets_deadline=meets_deadline,
    )
