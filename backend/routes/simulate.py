"""
POST /api/simulate     — Soumet un job, NERVE retourne le meilleur choix serveur + savings
POST /api/llm/analyze  — Envoie les donnees live au LLM pour une analyse en langage naturel
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from models import SimulateRequest, SimulateResponse
from engine.scoring import run_simulation

router = APIRouter(prefix="/api", tags=["Simulation"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="Simulate job placement → best AZ + savings",
)
async def simulate_job(req: SimulateRequest):
    """
    Le coeur de NERVE.
    Recoit un job (type, deadline, GPU requis) et retourne :
    - La decision (region, AZ, GPU, strategie)
    - Le fallback
    - La config de checkpointing
    - Les economies en USD/EUR
    - L'impact carbone
    - Le chemin serveur complet
    """
    return await run_simulation(req)


class LLMRequest(BaseModel):
    question: str = Field(
        "Analyse les donnees et recommande la meilleure strategie pour un fine-tuning LLaMA-7B.",
        example="Quel est le meilleur moment pour lancer un job de 24h GPU ?",
    )


@router.post("/llm/analyze", summary="Ask NERVE AI — LLM analysis of live data")
async def llm_analyze(req: LLMRequest):
    """
    Send live scraped data + user question to LLM (Claude/GPT).
    Returns AI-powered analysis in natural language.
    """
    from engine.llm import call_nerve_llm, build_llm_context

    context = await build_llm_context()
    prompt = f"Question utilisateur: {req.question}\n\nDonnees live NERVE:\n{context}"
    result = await call_nerve_llm(prompt)
    return {
        "question": req.question,
        "response": result,
        "data_source": "live scraper",
    }
