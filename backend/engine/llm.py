"""
NERVE Engine — Real LLM Integration
Envoie le JSON scrappe live + preprompt au LLM pour decision.
Supporte : Anthropic Claude, OpenAI GPT.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger("nerve.llm")

_PREPROMPT_PATHS = [
    Path(__file__).resolve().parent.parent.parent / "vision" / "nerve_llm_preprompt.txt",
    Path(__file__).resolve().parent.parent / "data" / "nerve_llm_preprompt.txt",
]


def _load_preprompt() -> str:
    for path in _PREPROMPT_PATHS:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return (
        "Tu es NERVE, un moteur d'optimisation FinOps/GreenOps pour le Cloud Computing GPU. "
        "Analyse les donnees JSON fournies et retourne ta decision au format JSON."
    )


def _get_provider() -> str:
    return os.getenv("NERVE_LLM_PROVIDER", "none")


def _get_model() -> str:
    defaults = {"anthropic": "claude-sonnet-4-20250514", "openai": "gpt-4o-mini"}
    return os.getenv("NERVE_LLM_MODEL", defaults.get(_get_provider(), ""))


async def call_nerve_llm(scraped_json: str) -> dict:
    """Send preprompt + live scraped JSON to real LLM API."""
    provider = _get_provider()
    preprompt = _load_preprompt()
    full_prompt = preprompt + "\n" + scraped_json

    log.info(f"LLM call — provider={provider}, prompt_len={len(full_prompt)}")

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"status": "error", "message": "ANTHROPIC_API_KEY not set in .env"}
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=_get_model(),
                max_tokens=4096,
                messages=[{"role": "user", "content": full_prompt}],
            )
            return _extract_json(response.content[0].text)
        except Exception as e:
            log.error(f"Anthropic API error: {e}")
            return {"status": "error", "message": str(e)}

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"status": "error", "message": "OPENAI_API_KEY not set in .env"}
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=_get_model(),
                messages=[
                    {"role": "system", "content": preprompt},
                    {"role": "user", "content": scraped_json},
                ],
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
            return _extract_json(response.choices[0].message.content)
        except Exception as e:
            log.error(f"OpenAI API error: {e}")
            return {"status": "error", "message": str(e)}

    return {
        "status": "no_provider",
        "message": f"Set NERVE_LLM_PROVIDER=anthropic|openai in .env",
        "prompt_length": len(full_prompt),
    }


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response (handles markdown fences)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        try:
            return json.loads(text[start:end].strip())
        except json.JSONDecodeError:
            pass
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except json.JSONDecodeError:
            pass
    return {"status": "parse_error", "raw_response": text[:2000]}


async def build_llm_context() -> str:
    """Build JSON context from live scraped data for LLM."""
    from engine.scraper import get_cache
    cache = get_cache()
    context = {
        "metadata": {
            "scrape_timestamp": cache.get("last_scrape"),
            "scrape_count": cache.get("scrape_count"),
            "source": "NERVE live scraper",
        },
        "gpu_prices": cache.get("gpu_prices", {}),
        "weather": cache.get("weather", {}),
        "carbon": cache.get("carbon", {}),
    }
    return json.dumps(context, indent=2, default=str)
