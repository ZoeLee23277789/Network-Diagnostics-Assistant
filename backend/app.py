from __future__ import annotations

import os
import threading
import json
import datetime
from copy import deepcopy

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler

from baseline import build_baseline, detect_anomalies
from diagnosis import diagnose, classify_root_cause, build_recommendation_plan
from llm_diagnosis import llm_diagnose
from collector_agent import collect_data


load_dotenv()

app = Flask(__name__)
CORS(app)

mongo_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db = mongo_client[os.getenv("DB_NAME", "wireless_troubleshooting")]
collection = db[os.getenv("COLLECTION_NAME", "records")]


def serialize_doc(doc):
    """Convert MongoDB-specific values to JSON-serializable values."""
    if isinstance(doc, list):
        return [serialize_doc(x) for x in doc]

    if isinstance(doc, dict):
        output = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                output[key] = str(value)
            elif isinstance(value, dict):
                output[key] = serialize_doc(value)
            elif isinstance(value, list):
                output[key] = [serialize_doc(v) for v in value]
            else:
                output[key] = value
        return output

    return doc


def _avg(values):
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def enrich_record(data: dict, prior_records: list[dict]) -> dict:
    """Run baseline, diagnosis, root cause, recommendation, and LLM."""
    location = data.get("location")

    location_baseline = build_baseline(prior_records, location=location)
    global_baseline = build_baseline(prior_records)

    baseline = (
        location_baseline
        if location_baseline.get("sample_count", 0) >= 2
        else global_baseline
    )

    anomaly_result = detect_anomalies(data, baseline)
    diagnosis_result = diagnose(data, anomaly_result)
    root_cause_result = classify_root_cause(data, diagnosis_result)
    recommendation_plan = build_recommendation_plan(data, root_cause_result)
    llm_result = llm_diagnose(
        data,
        anomaly_result,
        diagnosis_result,
        root_cause_result,
        recommendation_plan,
    )

    enriched = {
        **data,
        "baseline_analysis": anomaly_result,
        "rule_diagnosis": diagnosis_result,
        "root_cause": root_cause_result,
        "recommendation_plan": recommendation_plan,
        "llm_diagnosis": llm_result,
    }
    return enriched


# Auto-collection configuration
AUTO_COLLECT_LOCATION = os.getenv("AUTO_COLLECT_LOCATION", "auto_monitoring_site")
AUTO_COLLECT_ENVIRONMENT = os.getenv("AUTO_COLLECT_ENVIRONMENT", "lab")
AUTO_COLLECT_ENABLED = os.getenv("AUTO_COLLECT_ENABLED", "true").lower() == "true"
AUTO_COLLECT_INTERVAL = int(os.getenv("AUTO_COLLECT_INTERVAL", "300"))  # 300 seconds = 5 minutes


def auto_collect_worker():
    """Background worker that collects network data periodically."""
    try:
        print(f"[AutoCollect] Starting collection from {AUTO_COLLECT_LOCATION}...")
        record = collect_data(
            location=AUTO_COLLECT_LOCATION,
            environment=AUTO_COLLECT_ENVIRONMENT
        )
        
        # Get prior records for baseline calculation
        prior_records = list(collection.find({}).sort("_id", -1).limit(100))
        
        # Enrich the record with diagnosis
        enriched = enrich_record(record, prior_records)
        
        # Save to database
        result = collection.insert_one(enriched)
        print(f"[AutoCollect] Record saved: {result.inserted_id} at {enriched.get('timestamp')}")
        
    except Exception as e:
        print(f"[AutoCollect] Error during collection: {str(e)}")


def init_scheduler():
    """Initialize and start the background scheduler."""
    if not AUTO_COLLECT_ENABLED:
        print("[AutoCollect] Auto-collection is disabled")
        return
    
    scheduler = BackgroundScheduler()
    
    # Schedule the auto-collect job every N seconds
    scheduler.add_job(
        func=auto_collect_worker,
        trigger="interval",
        seconds=AUTO_COLLECT_INTERVAL,
        id="auto_collect_job",
        name="Auto Network Data Collection",
        replace_existing=True,
    )
    
    scheduler.start()
    print(f"[AutoCollect] Scheduler started. Collection interval: {AUTO_COLLECT_INTERVAL}s")
    
    return scheduler


# Initialize scheduler when the app starts
_scheduler = None
try:
    _scheduler = init_scheduler()
except Exception as e:
    print(f"[AutoCollect] Failed to initialize scheduler: {str(e)}")


@app.get("/api/health")
def health() -> tuple:
    return jsonify({"status": "ok"}), 200


@app.post("/api/records")
def create_record() -> tuple:
    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({"error": "Request body is empty or invalid JSON"}), 400

    prior_records = list(collection.find({}, {"_id": 0}))
    enriched = enrich_record(data, prior_records)

    insert_result = collection.insert_one(deepcopy(enriched))
    enriched["_id"] = str(insert_result.inserted_id)

    return jsonify(serialize_doc(enriched)), 201


@app.get("/api/records")
def get_records() -> tuple:
    limit = int(request.args.get("limit", 200))
    location = request.args.get("location")

    query = {}
    if location:
        query["location"] = location

    records = list(collection.find(query).sort("timestamp", -1).limit(limit))
    return jsonify(serialize_doc(records)), 200


@app.get("/api/summary")
def get_summary() -> tuple:
    records = list(collection.find({}, {"_id": 0}))

    total = len(records)
    high = sum(
        1 for r in records
        if r.get("rule_diagnosis", {}).get("severity") == "high"
    )
    medium = sum(
        1 for r in records
        if r.get("rule_diagnosis", {}).get("severity") == "medium"
    )
    normal = sum(
        1 for r in records
        if r.get("rule_diagnosis", {}).get("severity") == "normal"
    )

    avg_download = _avg([r.get("speedtest", {}).get("download_mbps") for r in records])
    avg_latency = _avg([r.get("speedtest", {}).get("latency_ms") for r in records])
    avg_signal = _avg([r.get("wifi", {}).get("signal_percent") for r in records])
    avg_health_score = _avg(
        [r.get("rule_diagnosis", {}).get("health_score") for r in records]
    )
    anomaly_count = sum(
        1 for r in records
        if r.get("baseline_analysis", {}).get("status") == "anomaly_detected"
    )

    return jsonify({
        "total_records": total,
        "high_severity": high,
        "medium_severity": medium,
        "normal": normal,
        "avg_download_mbps": avg_download,
        "avg_latency_ms": avg_latency,
        "avg_signal_percent": avg_signal,
        "avg_health_score": avg_health_score,
        "anomaly_count": anomaly_count,
    }), 200


@app.get("/api/locations")
def get_locations() -> tuple:
    locations = sorted(v for v in collection.distinct("location") if v)
    return jsonify(locations), 200


@app.get("/api/baseline/<location>")
def get_location_baseline(location: str) -> tuple:
    records = list(collection.find({"location": location}, {"_id": 0}))
    baseline = build_baseline(records, location=location)
    return jsonify(serialize_doc(baseline)), 200


@app.post("/api/reanalyze")
def reanalyze() -> tuple:
    """
    Rebuild all records using the current diagnosis + current API key.
    Useful after fixing OPENAI_API_KEY.
    """
    old_records = list(collection.find({}, {"_id": 0}).sort("timestamp", 1))
    collection.delete_many({})

    rebuilt = []
    for data in old_records:
        prior_records = rebuilt.copy()
        enriched = enrich_record(data, prior_records)
        insert_result = collection.insert_one(deepcopy(enriched))
        enriched["_id"] = str(insert_result.inserted_id)
        rebuilt.append(enriched)

    return jsonify({
        "status": "ok",
        "records": len(rebuilt),
        "message": "All records reanalyzed with current settings."
    }), 200


@app.post("/api/reset")
def reset_records() -> tuple:
    """
    Delete all records. Helpful when you want a clean demo dataset.
    """
    result = collection.delete_many({})
    return jsonify({
        "status": "ok",
        "deleted_count": result.deleted_count
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)