"""
NERVE Engine — Smart Checkpointing
Simule le protocole d'evacuation d'urgence Spot.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from models import CheckpointEvent, CheckpointSimulateRequest
from engine.scoring import record_checkpoint, record_eviction

# ── AZ voisines (mapping simple pour le hackathon) ───────────────────

_NEIGHBOR_AZ = {
    "fr-central-1": "fr-central-2",
    "fr-central-2": "fr-central-3",
    "fr-central-3": "fr-central-1",
    "we-1": "we-2",
    "we-2": "we-3",
    "we-3": "we-1",
    "uk-south-1": "uk-south-2",
    "uk-south-2": "uk-south-3",
    "uk-south-3": "uk-south-1",
}

# ── Vitesse de checkpoint estimee ────────────────────────────────────

S3_UPLOAD_GBPS = 1.2  # Debit moyen S3 intra-region


async def simulate_interruption(req: CheckpointSimulateRequest) -> CheckpointEvent:
    """
    Simule le protocole NERVE complet :
    1. Reception Spot Interruption Notice (T+0s)
    2. Signal PyTorch : sauvegarde checkpoint (T+2s)
    3. Upload checkpoint sur S3 (T+Xs selon taille)
    4. Cordon du noeud condamne (T+Xs)
    5. Nouveau Spot dans AZ voisine (T+30s)
    6. Telechargement checkpoint + reprise (T+45s)
    """
    now = datetime.now(timezone.utc)
    target_az = _NEIGHBOR_AZ.get(req.current_az, "fr-central-2")

    # Calcul du temps de sauvegarde
    checkpoint_size_gb = req.model_size_gb * 0.8  # Poids ~ 80% de la taille modele
    upload_duration_sec = checkpoint_size_gb / S3_UPLOAD_GBPS

    # Simulation async (petit delai pour le realisme)
    await asyncio.sleep(0.1)

    timeline = [
        {
            "time_sec": 0.0,
            "event": "Spot Interruption Notice recue (AWS metadata endpoint)",
        },
        {
            "time_sec": 1.5,
            "event": "NERVE signal PyTorch : torch.save() declenche",
        },
        {
            "time_sec": 1.5 + upload_duration_sec,
            "event": f"Checkpoint ({checkpoint_size_gb:.1f} GB) uploade sur S3",
        },
        {
            "time_sec": 2.0 + upload_duration_sec,
            "event": f"kubectl cordon {req.current_az} — noeud condamne",
        },
        {
            "time_sec": 25.0 + upload_duration_sec,
            "event": f"Nouveau GPU Spot provisionne dans {target_az}",
        },
        {
            "time_sec": 35.0 + upload_duration_sec,
            "event": "Checkpoint telecharge depuis S3 — torch.load()",
        },
        {
            "time_sec": 40.0 + upload_duration_sec,
            "event": f"Entrainement repris a {req.epoch_progress_pct}% — zero perte",
        },
    ]

    total_duration = timeline[-1]["time_sec"]

    record_checkpoint()
    record_eviction()

    return CheckpointEvent(
        job_id=req.job_id,
        status="migrated",
        checkpoint_saved=True,
        checkpoint_size_gb=round(checkpoint_size_gb, 2),
        save_duration_sec=round(upload_duration_sec, 2),
        from_az=req.current_az,
        to_az=target_az,
        downtime_ms=0,
        epoch_progress_pct=req.epoch_progress_pct,
        resumed=True,
        timeline=timeline,
    )
