from __future__ import annotations
from typing import Any, Dict, List


def _safe_avg(values: List[float]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def build_baseline(records: List[Dict[str, Any]], location: str | None = None) -> Dict[str, Any]:
    filtered = []
    for r in records:
        if location and r.get("location") != location:
            continue
        filtered.append(r)

    downloads = [r.get("speedtest", {}).get("download_mbps") for r in filtered]
    uploads = [r.get("speedtest", {}).get("upload_mbps") for r in filtered]
    latencies = [r.get("speedtest", {}).get("latency_ms") for r in filtered]
    jitters = [r.get("speedtest", {}).get("jitter_ms") for r in filtered]
    packet_losses = [r.get("speedtest", {}).get("packet_loss") for r in filtered]
    signals = [r.get("wifi", {}).get("signal_percent") for r in filtered]
    rssis = [r.get("wifi", {}).get("rssi_dbm") for r in filtered]

    return {
        "sample_count": len(filtered),
        "download_avg": _safe_avg(downloads),
        "upload_avg": _safe_avg(uploads),
        "latency_avg": _safe_avg(latencies),
        "jitter_avg": _safe_avg(jitters),
        "packet_loss_avg": _safe_avg(packet_losses),
        "signal_avg": _safe_avg(signals),
        "rssi_avg": _safe_avg(rssis),
    }


def detect_anomalies(record: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    speed = record.get("speedtest", {})
    wifi = record.get("wifi", {})
    anomalies = []

    download = speed.get("download_mbps")
    latency = speed.get("latency_ms")
    jitter = speed.get("jitter_ms")
    packet_loss = speed.get("packet_loss")
    signal = wifi.get("signal_percent")

    if baseline.get("download_avg") and download is not None and download < baseline["download_avg"] * 0.7:
        anomalies.append({
            "metric": "download_mbps",
            "type": "degradation",
            "message": f"Download is {round((1 - download / baseline['download_avg']) * 100, 1)}% below baseline.",
        })

    if baseline.get("latency_avg") and latency is not None and latency > baseline["latency_avg"] * 1.5:
        anomalies.append({
            "metric": "latency_ms",
            "type": "increase",
            "message": f"Latency is {round((latency / baseline['latency_avg'] - 1) * 100, 1)}% above baseline.",
        })

    if baseline.get("jitter_avg") and jitter is not None and jitter > max(20, baseline["jitter_avg"] * 2):
        anomalies.append({
            "metric": "jitter_ms",
            "type": "instability",
            "message": "Jitter is significantly above historical baseline.",
        })

    if packet_loss is not None and packet_loss > 0:
        anomalies.append({
            "metric": "packet_loss",
            "type": "loss",
            "message": f"Packet loss detected at {packet_loss}%.",
        })

    if baseline.get("signal_avg") and signal is not None and signal < baseline["signal_avg"] - 15:
        anomalies.append({
            "metric": "signal_percent",
            "type": "drop",
            "message": "Signal strength dropped noticeably compared to baseline.",
        })

    status = "normal" if not anomalies else "anomaly_detected"
    return {
        "status": status,
        "baseline": baseline,
        "anomalies": anomalies,
    }
