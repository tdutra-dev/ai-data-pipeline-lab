"""
services/insight_generator.py
──────────────────────────────────────────────────────────────────────────────
Calls OpenAI GPT-4o-mini to generate structured insights from mart data.

Produces three sections:
  • anomaly_summary    – unusual patterns in trading volume or user behaviour
  • risk_explanation   – plain-language breakdown of the top risk signals
  • operational_insight – actionable recommendations for the ops/compliance team

Degrades gracefully when OPENAI_API_KEY is not set (returns mock response).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

_MOCK_INSIGHTS = {
    "anomaly_summary": (
        "MOCK – OpenAI key not configured. "
        "Set OPENAI_API_KEY in .env to receive real AI-generated insights."
    ),
    "risk_explanation": (
        "MOCK – No API key. Risk signals are available in marts.mart_risk_signals."
    ),
    "operational_insight": (
        "MOCK – Run `make ai-insights` after setting OPENAI_API_KEY."
    ),
}


def _build_prompt(mart_data: dict[str, Any]) -> str:
    customer_activity = mart_data.get("customer_activity", [])
    risk_signals = mart_data.get("risk_signals", [])
    volume_summary = mart_data.get("volume_summary", [])

    return f"""You are a senior financial data analyst working for a regulated fintech trading platform.
Your task is to analyse the latest mart data from the data warehouse and produce a concise daily insight report.

## TOP CUSTOMER ACTIVITY (by notional value)
{json.dumps(customer_activity, indent=2, default=str)}

## RISK SIGNALS (ordered by risk score)
{json.dumps(risk_signals, indent=2, default=str)}

## TOP INSTRUMENTS BY VOLUME
{json.dumps(volume_summary, indent=2, default=str)}

Respond with a JSON object containing exactly these three keys:

{{
  "anomaly_summary": "<2-4 sentences describing any unusual trading patterns, volume spikes, or behavioural anomalies>",
  "risk_explanation": "<2-4 sentences explaining the most urgent risk signals, naming specific users and risk tiers>",
  "operational_insight": "<2-4 actionable recommendations for the operations or compliance team>"
}}

Be specific, cite data from the tables, and be concise. Do not include markdown – plain JSON only.
"""


def generate_insights(mart_data: dict[str, Any]) -> dict[str, Any]:
    """
    Returns structured insights dict.
    Falls back to mock response if API key is not set.
    """
    generated_at = datetime.now(timezone.utc).isoformat()

    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-..."):
        logger.warning("OPENAI_API_KEY not set – returning mock insights.")
        return {**_MOCK_INSIGHTS, "model": "mock", "generated_at": generated_at}

    # Import here so the service starts even without openai installed at build
    try:
        from openai import OpenAI  # noqa: PLC0415
    except ImportError:
        logger.error("openai package not installed.")
        return {**_MOCK_INSIGHTS, "model": "error", "generated_at": generated_at}

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": _build_prompt(mart_data)}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=600,
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        return {
            "anomaly_summary":    parsed.get("anomaly_summary", "—"),
            "risk_explanation":   parsed.get("risk_explanation", "—"),
            "operational_insight": parsed.get("operational_insight", "—"),
            "model":              response.model,
            "prompt_tokens":      response.usage.prompt_tokens,
            "completion_tokens":  response.usage.completion_tokens,
            "generated_at":       generated_at,
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("OpenAI call failed: %s", exc)
        raise
