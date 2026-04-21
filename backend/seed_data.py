from __future__ import annotations
import json
import os
from pathlib import Path
from pymongo import MongoClient
from baseline import build_baseline, detect_anomalies
from diagnosis import diagnose, classify_root_cause, build_recommendation_plan
from llm_diagnosis import llm_diagnose

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = ROOT / "sample_data" / "network_logs.jsonl"
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("DB_NAME", "wireless_troubleshooting")]
collection = db[os.getenv("COLLECTION_NAME", "records")]


def main() -> None:
    if not SAMPLE_PATH.exists():
        raise FileNotFoundError(f"Sample file not found: {SAMPLE_PATH}")

    records = []
    with SAMPLE_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            wifi = record.get("wifi", {})
            if "signal_percent" not in wifi and isinstance(wifi.get("signal"), str):
                wifi["signal_percent"] = int(wifi["signal"].replace("%", "").strip())
            if "rssi_dbm" not in wifi and wifi.get("rssi") is not None:
                try:
                    wifi["rssi_dbm"] = int(str(wifi.get("rssi")).strip())
                except ValueError:
                    wifi["rssi_dbm"] = None
            record["environment"] = record.get("environment", "unknown")
            records.append(record)

    collection.delete_many({})

    inserted = []
    for idx, record in enumerate(records):
        prior = inserted.copy()
        location = record.get("location")
        location_baseline = build_baseline(prior, location=location)
        global_baseline = build_baseline(prior, location=None)
        baseline = location_baseline if location_baseline.get("sample_count", 0) >= 2 else global_baseline

        anomaly_result = detect_anomalies(record, baseline)
        diagnosis_result = diagnose(record, anomaly_result)
        root_cause_result = classify_root_cause(record, diagnosis_result)
        recommendation_plan = build_recommendation_plan(record, root_cause_result)
        llm_result = llm_diagnose(record, anomaly_result, diagnosis_result, root_cause_result, recommendation_plan)

        enriched = {
            **record,
            "baseline_analysis": anomaly_result,
            "rule_diagnosis": diagnosis_result,
            "root_cause": root_cause_result,
            "recommendation_plan": recommendation_plan,
            "llm_diagnosis": llm_result,
        }
        collection.insert_one(enriched)
        inserted.append(enriched)

    print(f"Seeded {len(inserted)} records into MongoDB.")


if __name__ == "__main__":
    main()
