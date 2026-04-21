# import os
# import json
# from pathlib import Path
# from dotenv import load_dotenv
# from openai import OpenAI

# # 確保從正確的目錄讀取 .env
# env_path = Path(__file__).parent / ".env"
# load_dotenv(dotenv_path=env_path)


# def get_openai_client() -> OpenAI:
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         raise ValueError("OPENAI_API_KEY is missing from environment variables.")
#     # 調試：打印金鑰長度和末尾
#     print(f"[DEBUG] API Key length: {len(api_key)}, ends with: {api_key[-10:]}")
#     return OpenAI(api_key=api_key)


# def get_model_name() -> str:
#     return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# def build_prompt(
#     record: dict,
#     anomaly_result: dict,
#     diagnosis_result: dict,
#     root_cause_result: dict,
#     recommendation_plan: dict,
# ) -> str:
#     return f"""
# You are a wireless field application engineer assistant.

# Your task:
# 1. Read the network measurement record.
# 2. Read the anomaly detection result.
# 3. Read the rule-based diagnosis result.
# 4. Read the root cause analysis.
# 5. Read the recommendation plan.
# 6. Produce a concise engineering diagnosis.
# 7. Explain likely causes in practical terms.
# 8. Provide actionable next steps for field troubleshooting.
# 9. Keep the answer structured and professional.

# Measurement record:
# {json.dumps(record, indent=2, ensure_ascii=False)}

# Baseline / anomaly result:
# {json.dumps(anomaly_result, indent=2, ensure_ascii=False)}

# Rule-based diagnosis:
# {json.dumps(diagnosis_result, indent=2, ensure_ascii=False)}

# Root cause analysis:
# {json.dumps(root_cause_result, indent=2, ensure_ascii=False)}

# Recommendation plan:
# {json.dumps(recommendation_plan, indent=2, ensure_ascii=False)}

# Return JSON with exactly these keys:
# - summary
# - engineer_note
# - customer_friendly_explanation
# - likely_causes
# - suggested_actions
# - confidence

# Rules:
# - likely_causes must be a list of strings
# - suggested_actions must be a list of strings
# - confidence must be one of: low, medium, high
# - Do not invent unavailable metrics
# - Base your answer only on the provided data
# - Keep the response concise, useful, and field-support oriented
# """.strip()


# def llm_diagnose(
#     record: dict,
#     anomaly_result: dict,
#     diagnosis_result: dict,
#     root_cause_result: dict,
#     recommendation_plan: dict,
# ) -> dict:
#     try:
#         client = get_openai_client()
#         model = get_model_name()

#         prompt = build_prompt(
#             record,
#             anomaly_result,
#             diagnosis_result,
#             root_cause_result,
#             recommendation_plan,
#         )

#         response = client.chat.completions.create(
#             model=model,
#             messages=[
#                 {"role": "user", "content": prompt}
#             ],
#         )

#         text = response.choices[0].message.content.strip()

#         try:
#             return json.loads(text)
#         except json.JSONDecodeError:
#             return {
#                 "summary": "LLM returned a non-JSON response.",
#                 "engineer_note": text,
#                 "customer_friendly_explanation": text,
#                 "likely_causes": diagnosis_result.get("possible_causes", []),
#                 "suggested_actions": diagnosis_result.get("suggested_actions", []),
#                 "confidence": "low",
#             }

#     except Exception as e:
#         return {
#             "summary": f"LLM request failed: {str(e)}",
#             "engineer_note": "LLM request failed. Falling back to rule-based output.",
#             "customer_friendly_explanation": "The system could not generate the AI explanation, but rule-based diagnostics are still available.",
#             "likely_causes": diagnosis_result.get("possible_causes", []),
#             "suggested_actions": diagnosis_result.get("suggested_actions", []),
#             "confidence": "low",
#         }

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from environment variables.")
    print(f"[DEBUG] API Key length: {len(api_key)}, ends with: {api_key[-10:]}")
    return OpenAI(api_key=api_key)


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def build_prompt(
    record: dict,
    anomaly_result: dict,
    diagnosis_result: dict,
    root_cause_result: dict,
    recommendation_plan: dict,
) -> str:
    baseline = anomaly_result.get("baseline", {})
    speed = record.get("speedtest", {})
    wifi = record.get("wifi", {})
    
    # Build baseline comparison strings
    comparisons = []
    if baseline.get("download_avg") is not None:
        current_dl = speed.get("download_mbps", "N/A")
        baseline_dl = baseline.get("download_avg", "N/A")
        comparisons.append(f"Download: {current_dl} Mbps (Baseline: {baseline_dl} Mbps)")
    
    if baseline.get("latency_avg") is not None:
        current_lat = speed.get("latency_ms", "N/A")
        baseline_lat = baseline.get("latency_avg", "N/A")
        comparisons.append(f"Latency: {current_lat} ms (Baseline: {baseline_lat} ms)")
    
    if baseline.get("packet_loss_avg") is not None:
        current_pl = speed.get("packet_loss", "N/A")
        baseline_pl = baseline.get("packet_loss_avg", "N/A")
        comparisons.append(f"Packet Loss: {current_pl}% (Baseline: {baseline_pl}%)")
    
    if baseline.get("signal_avg") is not None:
        current_sig = wifi.get("signal_percent", "N/A")
        baseline_sig = baseline.get("signal_avg", "N/A")
        comparisons.append(f"Signal: {current_sig}% (Baseline: {baseline_sig}%)")
    
    baseline_comparison = "\\n".join(comparisons) if comparisons else "No baseline available"
    
    return f"""
You are a wireless field application engineer assistant.

TASK: Analyze the network measurement and produce a professional engineering diagnosis.

MEASUREMENT DATA:
{json.dumps(record, indent=2, ensure_ascii=False)}

BASELINE COMPARISON (vs historical data):
{baseline_comparison}

ANOMALY DETECTION:
{json.dumps(anomaly_result, indent=2, ensure_ascii=False)}

RULE-BASED DIAGNOSIS:
{json.dumps(diagnosis_result, indent=2, ensure_ascii=False)}

ROOT CAUSE ANALYSIS:
{json.dumps(root_cause_result, indent=2, ensure_ascii=False)}

RECOMMENDATION PLAN:
{json.dumps(recommendation_plan, indent=2, ensure_ascii=False)}

OUTPUT REQUIREMENTS:
Return JSON with EXACTLY these keys:
- summary: Brief technical summary of the network state
- engineer_note: Engineering metrics and observations (Cisco/telecom style)
- customer_friendly_explanation: Non-technical user explanation
- likely_causes: List of strings - specific causes identified
- suggested_actions: List of strings - actionable troubleshooting steps
- confidence: One of "low", "medium", "high" - confidence in diagnosis

ENGINEER_NOTE MUST INCLUDE:
- Specific metric deviations (with baseline comparison)
- Performance status (e.g., "Packet loss slightly above baseline (0.05%)")
- No critical throughput drops if applicable

RULES:
- Base answers ONLY on provided data
- If a cause is unknown, explain why (e.g., "Multiple minor anomalies, no single dominant cause")
- Include baseline comparison percentages when available
- Keep responses concise and field-support oriented
- Be specific, avoid vague language like "general degradation"
- Format numbers with 2 decimal places
""".strip()


def llm_diagnose(
    record: dict,
    anomaly_result: dict,
    diagnosis_result: dict,
    root_cause_result: dict,
    recommendation_plan: dict,
) -> dict:
    try:
        client = get_openai_client()
        model = get_model_name()

        prompt = build_prompt(
            record,
            anomaly_result,
            diagnosis_result,
            root_cause_result,
            recommendation_plan,
        )

        response = client.responses.create(
            model=model,
            input=prompt,
        )

        text = response.output_text.strip()

        # Check if the response is wrapped in markdown code block
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "summary": "LLM returned a non-JSON response.",
                "engineer_note": text,
                "customer_friendly_explanation": text,
                "likely_causes": diagnosis_result.get("possible_causes", []),
                "suggested_actions": diagnosis_result.get("suggested_actions", []),
                "confidence": "low",
            }

    except Exception as e:
        return {
            "summary": f"LLM request failed: {str(e)}",
            "engineer_note": "LLM request failed. Falling back to rule-based output.",
            "customer_friendly_explanation": "The system could not generate the AI explanation, but rule-based diagnostics are still available.",
            "likely_causes": diagnosis_result.get("possible_causes", []),
            "suggested_actions": diagnosis_result.get("suggested_actions", []),
            "confidence": "low",
        }