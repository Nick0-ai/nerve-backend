"""
NERVE Engine — LLM Integration
Envoie le JSON scrappe + preprompt a l'API LLM pour decision.
Stub pour le hackathon — sera branche sur Claude/GPT/Mistral.
"""

from __future__ import annotations

from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────

_VISION_DIR = Path(__file__).resolve().parent.parent.parent / "vision"
_PREPROMPT_PATH = _VISION_DIR / "nerve_llm_preprompt.txt"

LLM_PROVIDER: str = "stub"  # "anthropic" | "openai" | "mistral" | "stub"
LLM_MODEL: str = ""
LLM_API_KEY: str = ""


def _load_preprompt() -> str:
    """Charge le preprompt depuis le fichier."""
    if _PREPROMPT_PATH.exists():
        return _PREPROMPT_PATH.read_text(encoding="utf-8")
    return "Tu es NERVE, un optimiseur FinOps Cloud GPU."


def configure_llm(provider: str, model: str, api_key: str):
    """Configure le provider LLM a utiliser."""
    global LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
    LLM_PROVIDER = provider
    LLM_MODEL = model
    LLM_API_KEY = api_key


async def call_nerve_llm(scraped_json: str) -> dict:
    """
    Envoie preprompt + JSON scrappe au LLM.
    Retourne la decision structuree.

    TODO (Etape 3) : Brancher sur l'API reelle.
    """
    preprompt = _load_preprompt()
    full_prompt = preprompt + "\n" + scraped_json

    if LLM_PROVIDER == "stub":
        # Stub : retourne une decision hardcodee pour la demo
        return {
            "status": "stub",
            "message": "LLM non configure — utilise le scoring local",
            "prompt_length": len(full_prompt),
        }

    # ── Anthropic (Claude) ───────────────────────────────────────
    if LLM_PROVIDER == "anthropic":
        # import anthropic
        # client = anthropic.Anthropic(api_key=LLM_API_KEY)
        # response = client.messages.create(
        #     model=LLM_MODEL,
        #     max_tokens=2048,
        #     messages=[{"role": "user", "content": full_prompt}],
        # )
        # return json.loads(response.content[0].text)
        pass

    # ── OpenAI (GPT) ─────────────────────────────────────────────
    if LLM_PROVIDER == "openai":
        # import openai
        # client = openai.OpenAI(api_key=LLM_API_KEY)
        # response = client.chat.completions.create(
        #     model=LLM_MODEL,
        #     messages=[{"role": "user", "content": full_prompt}],
        # )
        # return json.loads(response.choices[0].message.content)
        pass

    return {"status": "error", "message": f"Provider '{LLM_PROVIDER}' non supporte"}
