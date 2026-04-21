from __future__ import annotations
from typing import Any, Dict, List


def diagnose(record: Dict[str, Any], anomaly_result: Dict[str, Any] | None = None) -> Dict[str, Any]:
    speed = record.get("speedtest", {})
    wifi = record.get("wifi", {})

    download = float(speed.get("download_mbps", 0) or 0)
    upload = float(speed.get("upload_mbps", 0) or 0)
    latency = float(speed.get("latency_ms", 0) or 0)
    jitter = float(speed.get("jitter_ms", 0) or 0)
    packet_loss = float(speed.get("packet_loss", 0) or 0)
    signal = float(wifi.get("signal_percent", 0) or 0)
    rssi = float(wifi.get("rssi_dbm", -100) or -100)
    band = str(wifi.get("band", "unknown"))

    issues: List[str] = []
    causes: List[str] = []
    actions: List[str] = []
    severity = "normal"

    if latency > 100:
        issues.append("Severe latency detected")
        severity = "high"
    elif latency > 50:
        issues.append("High latency detected")
        severity = "medium"

    if packet_loss >= 3:
        issues.append("Significant packet loss detected")
        severity = "high"
    elif packet_loss > 0:
        issues.append("Packet loss detected")
        if severity == "normal":
            severity = "medium"

    if signal < 50 or rssi < -75:
        issues.append("Very weak signal")
        causes.append("Distance from AP or heavy obstruction")
        actions.extend([
            "Move closer to the access point.",
            "Reduce obstacles between the client and AP.",
        ])
        severity = "high"
    elif signal < 70 or rssi < -67:
        issues.append("Weak signal")
        causes.append("Signal attenuation or partial obstruction")
        actions.append("Reposition closer to the access point.")
        if severity == "normal":
            severity = "medium"

    if download < 100:
        issues.append("Severe throughput degradation")
        causes.append("Possible congestion, interference, or poor link quality")
        actions.extend([
            "Run comparison tests at off-peak hours.",
            "Compare with another nearby test point.",
        ])
        severity = "high"
    elif download < 200:
        issues.append("Below expected throughput")
        causes.append("Possible congestion or band/channel contention")
        actions.append("Retry the test in another location or time window.")
        if severity == "normal":
            severity = "medium"

    if jitter > 20:
        issues.append("Unstable connection")
        causes.append("Interference or inconsistent link quality")
        actions.append("Check for crowded or noisy wireless environments.")
        if severity == "normal":
            severity = "medium"

    if band == "2.4 GHz":
        causes.append("2.4 GHz may experience heavier interference in dense environments")
        actions.append("Prefer 5 GHz or 6 GHz when available.")

    if anomaly_result and anomaly_result.get("anomalies"):
        issues.append("Performance deviates from baseline")
        actions.append("Compare the current test against the historical baseline for this location.")
        if severity == "normal":
            severity = "medium"

    if not issues:
        issues.append("No critical issue detected")
        causes.append("Current network metrics appear healthy")
        actions.append("Use this record as a performance baseline.")

    actions = list(dict.fromkeys(actions))
    causes = list(dict.fromkeys(causes))
    issues = list(dict.fromkeys(issues))

    health_score = _health_score(download, upload, latency, jitter, packet_loss, signal, rssi)
    priority = "CRITICAL" if health_score < 50 or severity == "high" else "MEDIUM" if health_score < 70 or severity == "medium" else "LOW"
    
    return {
        "issues": issues,
        "possible_causes": causes,
        "suggested_actions": actions,
        "severity": severity,
        "priority": priority,
        "health_score": health_score,
    }


def classify_root_cause(record: Dict[str, Any], diagnosis_result: Dict[str, Any]) -> Dict[str, Any]:
    speed = record.get("speedtest", {})
    wifi = record.get("wifi", {})

    download = float(speed.get("download_mbps", 0) or 0)
    latency = float(speed.get("latency_ms", 0) or 0)
    jitter = float(speed.get("jitter_ms", 0) or 0)
    packet_loss = float(speed.get("packet_loss", 0) or 0)
    signal = float(wifi.get("signal_percent", 0) or 0)
    rssi = float(wifi.get("rssi_dbm", -100) or -100)
    band = str(wifi.get("band", "unknown"))

    root_cause_category = "Healthy"
    confidence = 0.6
    likely_causes: List[str] = []
    evidence: List[str] = []

    if signal < 70 or rssi < -67:
        root_cause_category = "Signal Quality Issue"
        confidence = 0.86
        likely_causes.append(f"Weak signal ({signal}% / {rssi} dBm)")
        evidence.extend([f"signal={signal}%", f"rssi={rssi} dBm"])
    elif packet_loss > 1:
        root_cause_category = "Network Quality Degradation"
        confidence = 0.80
        likely_causes.append("Significant packet loss detected")
        if latency > 50:
            likely_causes.append("Possible congestion or contention")
        evidence.extend([f"packet_loss={packet_loss}%", f"latency={latency} ms"])
    elif packet_loss > 0 and latency > 50:
        root_cause_category = "Network Quality Degradation"
        confidence = 0.72
        likely_causes.extend(["Minor packet loss", "Elevated latency", "Possible congestion"])
        evidence.extend([f"latency={latency} ms", f"packet_loss={packet_loss}%"])
    elif jitter > 20:
        root_cause_category = "Stability/Interference Issue"
        confidence = 0.78
        likely_causes.append("High jitter detected")
        if band == "2.4 GHz":
            likely_causes.append(f"Possible interference on {band}")
        evidence.append(f"jitter={jitter} ms")
    elif download < 200 and band == "2.4 GHz":
        root_cause_category = "Band Interference"
        confidence = 0.75
        likely_causes.append("2.4 GHz may experience heavier interference")
        evidence.extend([f"download={download} Mbps", f"band={band}"])
    elif diagnosis_result.get("severity") == "normal":
        root_cause_category = "Healthy"
        confidence = 0.9
        likely_causes.append("All metrics within healthy range")
        evidence.append("No critical issues detected")
    else:
        root_cause_category = "Network Quality Degradation"
        confidence = 0.65
        likely_causes.extend(["Multiple minor anomalies detected", "No single dominant cause"])
        evidence.append("Metrics indicate minor degradation across multiple indicators")

    return {
        "root_cause_category": root_cause_category,
        "likely_causes": likely_causes,
        "confidence": confidence,
        "evidence": evidence,
    }


def build_recommendation_plan(record: Dict[str, Any], root_cause_result: Dict[str, Any]) -> Dict[str, Any]:
    rc = root_cause_result.get("root_cause_category", "Unknown")
    priority = "MEDIUM"
    actions: List[Dict[str, Any]] = []

    if rc == "Signal Quality Issue":
        priority = "HIGH"
        actions = [
            {
                "action": "Move closer to the AP and retest.",
                "reason": "Weak RSSI / signal suggests coverage or obstruction issues.",
                "expected_improvement": "Lower latency and more stable throughput.",
            },
            {
                "action": "Test from a less obstructed line-of-sight location.",
                "reason": "Walls and obstacles can attenuate Wi-Fi signal.",
                "expected_improvement": "Improved RSSI and reduced retransmissions.",
            },
        ]
    elif rc == "Network Quality Degradation":
        priority = "MEDIUM"
        actions = [
            {
                "action": "Retest during off-peak hours.",
                "reason": "Issues may indicate congestion or temporary network instability.",
                "expected_improvement": "Higher throughput and lower delay.",
            },
            {
                "action": "Compare nearby locations or alternate AP coverage.",
                "reason": "Issues may be localized to a specific AP or coverage cell.",
                "expected_improvement": "Identify whether the issue is site-specific.",
            },
        ]
    elif rc == "Stability/Interference Issue":
        priority = "MEDIUM"
        actions = [
            {
                "action": "Switch to 5 GHz or 6 GHz if available.",
                "reason": "High jitter may reflect interference or unstable airtime conditions.",
                "expected_improvement": "Reduced jitter and smoother connectivity.",
            },
            {
                "action": "Retest away from crowded RF environments.",
                "reason": "Nearby devices and dense environments can increase instability.",
                "expected_improvement": "More consistent latency.",
            },
        ]
    elif rc == "Band Interference":
        priority = "MEDIUM"
        actions = [
            {
                "action": "Prefer 5 GHz or 6 GHz over 2.4 GHz.",
                "reason": "2.4 GHz is more prone to interference in dense environments.",
                "expected_improvement": "Higher throughput and better stability.",
            }
        ]
    elif rc == "Healthy":
        priority = "LOW"
        actions = [
            {
                "action": "Save this measurement as a reference baseline.",
                "reason": "Current network conditions look healthy.",
                "expected_improvement": "Supports future anomaly detection.",
            }
        ]
    else:
        priority = "MEDIUM"
        actions = [
            {
                "action": "Run repeated tests across time and nearby locations.",
                "reason": "The issue is degraded but not yet uniquely classified.",
                "expected_improvement": "Better isolation of the dominant cause.",
            }
        ]

    return {"actions": actions, "priority": priority}


def _health_score(download: float, upload: float, latency: float, jitter: float, packet_loss: float, signal: float, rssi: float) -> int:
    """Calculate health score (0-100) based on network metrics.
    
    Thresholds: 90-100=healthy, 70-89=degraded, 50-69=poor, <50=critical
    """
    score = 100
    
    # Packet loss is most critical
    if packet_loss >= 5:
        score -= 35
    elif packet_loss >= 1:
        score -= 20
    elif packet_loss > 0:
        score -= 10
    
    # Signal quality
    if rssi < -75 or signal < 50:
        score -= 25
    elif rssi < -67 or signal < 70:
        score -= 15
    
    # Latency
    if latency > 100:
        score -= 20
    elif latency > 50:
        score -= 15
    
    # Jitter
    if jitter > 20:
        score -= 15
    
    # Throughput
    if download < 100:
        score -= 20
    elif download < 200:
        score -= 10
    
    if upload < 50:
        score -= 10
    
    return max(0, min(100, score))
