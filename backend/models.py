"""
NERVE — Pydantic Models
Tous les schemas request/response de l'API.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────

class JobType(str, Enum):
    LLM_FINE_TUNING = "llm_fine_tuning"
    LLM_INFERENCE = "llm_inference"
    RENDERING_3D = "rendering_3d"
    DATA_ETL = "data_etl"


class Availability(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class CarbonIndex(str, Enum):
    VERY_LOW = "very low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very high"


class StartStrategy(str, Enum):
    IMMEDIATE = "immediate"
    TIME_SHIFTED = "time_shifted"


class InterruptionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ── GPU & AZ ─────────────────────────────────────────────────────────

class GpuInstance(BaseModel):
    sku: str = Field(..., example="Standard_NC6s_v3")
    gpu_name: str = Field(..., example="Tesla V100 (16GB)")
    gpu_count: int = 1
    vcpus: int = 6
    ram_gb: int = 112
    spot_price_usd_hr: float = Field(..., example=0.6616)
    ondemand_price_usd_hr: float = Field(..., example=3.58)
    savings_pct: float = Field(..., example=81.5)
    availability: Availability = Availability.HIGH


class AZInfo(BaseModel):
    az_id: str = Field(..., example="fr-central-1")
    az_name: str = Field(..., example="France Central AZ-1")
    gpu_instances: list[GpuInstance] = []
    carbon_intensity_gco2_kwh: float = Field(..., example=56.0)
    carbon_index: CarbonIndex = CarbonIndex.LOW
    temperature_c: float = Field(..., example=11.0)
    wind_kmh: float = Field(..., example=15.4)
    score: Optional[float] = Field(None, description="Score NERVE (lower = better)")


class RegionInfo(BaseModel):
    region_id: str = Field(..., example="francecentral")
    region_name: str = Field(..., example="France Central")
    cloud_provider: str = Field(..., example="azure")
    location: str = Field(..., example="Paris, France")
    availability_zones: list[AZInfo] = []


# ── Requests ─────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    job_type: JobType = JobType.LLM_FINE_TUNING
    model_name: str = Field("LLaMA-7B", example="LLaMA-7B")
    estimated_gpu_hours: float = Field(24.0, gt=0, example=24.0)
    deadline: datetime = Field(..., example="2026-02-22T08:00:00Z")
    min_gpu_memory_gb: int = Field(16, ge=4, example=16)
    framework: str = Field("pytorch", example="pytorch")
    checkpoint_interval_min: int = Field(30, ge=5, example=30)
    preferred_region: Optional[str] = Field(None, example="francecentral")


class CheckpointSimulateRequest(BaseModel):
    job_id: str = Field(..., example="fine-tune-llama-7b")
    current_region: str = Field("francecentral", example="francecentral")
    current_az: str = Field("fr-central-1", example="fr-central-1")
    current_sku: str = Field("Standard_NC6s_v3", example="Standard_NC6s_v3")
    epoch_progress_pct: float = Field(42.0, ge=0, le=100, example=42.0)
    model_size_gb: float = Field(14.0, gt=0, example=14.0)


class TimeShiftRequest(BaseModel):
    job_type: JobType = JobType.LLM_FINE_TUNING
    estimated_gpu_hours: float = Field(24.0, gt=0, example=24.0)
    deadline: datetime = Field(..., example="2026-02-22T08:00:00Z")
    min_gpu_memory_gb: int = Field(16, ge=4, example=16)
    preferred_region: Optional[str] = Field(None, example="francecentral")
    flexible: bool = Field(True, description="Le job peut-il etre decale ?")


# ── Responses ────────────────────────────────────────────────────────

class Decision(BaseModel):
    primary_region: str
    primary_az: str
    gpu_sku: str
    gpu_name: str
    spot_price_usd_hr: float
    start_strategy: StartStrategy
    optimal_start_time: Optional[datetime] = None
    reason: str


class Fallback(BaseModel):
    secondary_az: str
    secondary_sku: str
    fallback_reason: str


class CheckpointConfig(BaseModel):
    recommended_interval_min: int
    storage_target: str = "s3"
    estimated_checkpoint_size_gb: float
    reason: str


class Savings(BaseModel):
    spot_cost_total_usd: float
    ondemand_cost_total_usd: float
    savings_usd: float
    savings_eur: float
    savings_pct: float
    time_shift_extra_savings_usd: float = 0.0


class GreenImpact(BaseModel):
    carbon_intensity_gco2_kwh: float
    total_energy_kwh: float
    total_co2_grams: float
    co2_vs_worst_region_grams: float
    co2_saved_grams: float
    equivalent: str = Field(..., example="Equivalent a 2.3 km en voiture evites")


class ServerStep(BaseModel):
    step: int
    action: str
    region: str
    az: str
    gpu: str
    time: datetime


class RiskAssessment(BaseModel):
    spot_interruption_probability: InterruptionRisk
    eviction_mitigation: str
    max_evictions_per_hour: int = 2


class SimulateResponse(BaseModel):
    decision: Decision
    fallback: Fallback
    checkpointing: CheckpointConfig
    savings: Savings
    green_impact: GreenImpact
    server_path: list[ServerStep]
    risk_assessment: RiskAssessment


class CheckpointEvent(BaseModel):
    job_id: str
    status: str = Field(..., example="saving")
    checkpoint_saved: bool = False
    checkpoint_size_gb: float = 0.0
    save_duration_sec: float = 0.0
    from_az: str
    to_az: str
    downtime_ms: int = 0
    epoch_progress_pct: float
    resumed: bool = False
    timeline: list[dict]


class TimeShiftPlan(BaseModel):
    recommended: bool
    optimal_window_start: Optional[datetime] = None
    optimal_window_end: Optional[datetime] = None
    reason: str
    estimated_spot_price_usd_hr: float
    current_spot_price_usd_hr: float
    price_reduction_pct: float
    carbon_reduction_pct: float
    meets_deadline: bool


class DashboardStats(BaseModel):
    total_jobs_managed: int
    total_savings_usd: float
    total_savings_eur: float
    total_co2_saved_grams: float
    total_checkpoints_saved: int
    total_evictions_handled: int
    avg_savings_pct: float
    uptime_pct: float = 100.0
    regions_monitored: list[str]
    last_updated: datetime


# ── WebSocket Events ─────────────────────────────────────────────────

class WSEventType(str, Enum):
    AZ_PRICE_UPDATE = "az_price_update"
    CHECKPOINT_EVENT = "checkpoint_event"
    MIGRATION_COMPLETE = "migration_complete"
    TIMESHIFT_SCHEDULED = "timeshift_scheduled"
    SPOT_INTERRUPTION = "spot_interruption"


class WSEvent(BaseModel):
    type: WSEventType
    timestamp: datetime
    data: dict
