from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from environment variables.")
    print("[DEBUG] OpenAI API key loaded.")
    return OpenAI(api_key=api_key)


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def ask_llm(records: list[dict], question: str) -> str:
    client = get_openai_client()
    model = get_model_name()
    prompt = f"""
You are a professional wireless network Field Application Engineer assistant.
Answer the user's question using only the information in the provided recent diagnostic records (last 10 measurements).
Do not invent new issues or causes. Base your analysis on trends and patterns across these records.

RECENT RECORDS (last 10):
{_safe_json(records)}

QUESTION:
{question}

Answer concisely and clearly for a technical audience, considering trends across the recent measurements.
""".strip()

    response = client.responses.create(model=model, input=prompt)
    text = response.output_text.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    elif text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
    return text


def _safe_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _fallback_customer(diagnosis_result: dict, root_cause_result: dict) -> dict:
    rc = root_cause_result.get("root_cause_category", "Unknown")
    severity = diagnosis_result.get("severity", "normal")
    if rc == "Healthy" or severity == "normal":
        return {
            "status": "Healthy",
            "message": "The connection looks healthy in this test. No major Wi-Fi signal, packet loss, or basic connectivity issue was detected.",
            "next_step": "Use this result as a healthy baseline and retest during the issue window if the problem happens again.",
        }
    return {
        "status": "Degraded",
        "message": "The connection shows signs of degraded network performance. The system found measurable indicators that may affect user experience.",
        "next_step": "Retest at the same location and compare with another AP or time window.",
    }


def _fallback_engineer(diagnosis_result: dict, root_cause_result: dict, recommendation_plan: dict) -> dict:
    return {
        "status": "Healthy" if diagnosis_result.get("severity") == "normal" else "Degraded",
        "severity": diagnosis_result.get("severity", "normal"),
        "root_cause": root_cause_result.get("root_cause_category", "Unknown"),
        "key_observations": diagnosis_result.get("evidence", [])[:8],
        "diagnosis": "; ".join(root_cause_result.get("likely_causes", [])) or "Rule-based diagnosis generated from available measurements.",
        "recommended_next_steps": [a.get("action") for a in recommendation_plan.get("actions", []) if a.get("action")],
        "data_to_collect_if_issue_repeats": [
            "AP/router logs",
            "Nearby AP/channel scan",
            "Channel utilization / noise information if available",
            "Client adapter and driver version",
            "Repeat speedtest and ping during the issue window",
        ],
    }


def build_prompt(
    record: dict,
    anomaly_result: dict,
    diagnosis_result: dict,
    root_cause_result: dict,
    recommendation_plan: dict,
) -> str:
    return f"""
You are a wireless Field Application Engineer assistant.

Your job is to convert structured diagnostic data into two outputs:
1. A customer-friendly explanation.
2. A structured engineer note.

Do NOT use the LLM as the only diagnosis engine. The rule-based diagnosis and root-cause data below are the source of truth.

MEASUREMENT DATA:
{_safe_json(record)}

BASELINE / ANOMALY RESULT:
{_safe_json(anomaly_result)}

RULE-BASED DIAGNOSIS:
{_safe_json(diagnosis_result)}

ROOT CAUSE ANALYSIS:
{_safe_json(root_cause_result)}

RECOMMENDATION PLAN:
{_safe_json(recommendation_plan)}

Return valid JSON only. Do not use markdown.
Use EXACTLY this schema:

{{
  "summary": "One short technical summary.",
  "customer_friendly_explanation": {{
    "status": "Healthy | Degraded | Issue Detected",
    "key_findings": [
      "Finding 1: Brief description with key metric",
      "Finding 2: Brief description with key metric"
    ],
    "message": "Simple non-technical explanation with more details.",
    "next_steps": [
      "Step 1: Specific action to take",
      "Step 2: Additional recommendation if needed"
    ]
  }},
  "engineer_note": {{
    "status": "Healthy | Degraded | Issue Detected",
    "severity": "normal | medium | high",
    "root_cause": "Detailed root cause explanation with evidence.",
    "key_observations": [
      "Observation 1: Detailed metric analysis with comparison",
      "Observation 2: Additional technical detail",
      "Observation 3: Pattern or trend identified"
    ],
    "diagnosis": "Detailed engineering interpretation with multiple paragraphs if needed.",
    "recommended_next_steps": [
      "Step 1: Detailed technical action with reasoning",
      "Step 2: Follow-up measurement or verification",
      "Step 3: Long-term monitoring or configuration change"
    ],
    "data_to_collect_if_issue_repeats": [
      "Specific log type and location",
      "Detailed scan parameters",
      "Additional metrics to capture",
      "Environmental factors to note"
    ]
  }},
  "likely_causes": ["cause 1"],
  "suggested_actions": ["action 1"],
  "confidence": "low | medium | high"
}}

CUSTOMER EXPLANATION RULES:
- Use simple language but provide detailed explanations.
- Include 2-4 key findings in bullet points with specific metrics.
- Provide a comprehensive message explaining the situation.
- List 2-3 specific next steps the user should take.
- Be helpful and actionable, not just diagnostic.

ENGINEER NOTE RULES:
- Provide detailed, technical analysis with multiple observations.
- Include 3-5 key observations with specific metrics and comparisons.
- Give a thorough diagnosis with reasoning and evidence.
- List 3-5 detailed recommended next steps with technical details.
- Include comprehensive data collection requirements for future issues.
- Use structured bullet points for all lists.
- Include why the root cause was selected with supporting data.
- If healthy, explain what makes it a good baseline.
- Base answers ONLY on provided data but be thorough in analysis.
""".strip()


def llm_diagnose(
    record: dict,
    anomaly_result: dict,
    diagnosis_result: dict,
    root_cause_result: dict,
    recommendation_plan: dict,
) -> Dict[str, Any]:
    try:
        client = get_openai_client()
        model = get_model_name()
        prompt = build_prompt(record, anomaly_result, diagnosis_result, root_cause_result, recommendation_plan)

        response = client.responses.create(model=model, input=prompt)
        text = response.output_text.strip()

        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()

        parsed = json.loads(text)

        # Backward-compatible safety normalization.
        if not isinstance(parsed.get("customer_friendly_explanation"), dict):
            parsed["customer_friendly_explanation"] = {
                "status": "Degraded" if diagnosis_result.get("severity") != "normal" else "Healthy",
                "message": str(parsed.get("customer_friendly_explanation", "")),
                "next_step": "Follow the recommended actions from the diagnostic result.",
            }
        if not isinstance(parsed.get("engineer_note"), dict):
            parsed["engineer_note"] = _fallback_engineer(diagnosis_result, root_cause_result, recommendation_plan)
        return parsed

    except Exception as e:
        return {
            "summary": f"LLM unavailable. Using rule-based diagnosis. Error: {str(e)}",
            "customer_friendly_explanation": _fallback_customer(diagnosis_result, root_cause_result),
            "engineer_note": _fallback_engineer(diagnosis_result, root_cause_result, recommendation_plan),
            "likely_causes": root_cause_result.get("likely_causes", diagnosis_result.get("possible_causes", [])),
            "suggested_actions": diagnosis_result.get("suggested_actions", []),
            "confidence": "low",
        }
