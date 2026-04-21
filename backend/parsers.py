from __future__ import annotations
import re
from typing import Dict, Any


def parse_wifi_info(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    patterns = {
        "ssid": r"^\s*SSID\s*:\s*(.+)$",
        "band": r"^\s*Band\s*:\s*(.+)$",
        "channel": r"^\s*Channel\s*:\s*(.+)$",
        "radio_type": r"^\s*Radio type\s*:\s*(.+)$",
        "signal": r"^\s*Signal\s*:\s*(.+)$",
        "rssi": r"^\s*Rssi\s*:\s*(.+)$",
        "receive_rate_mbps": r"^\s*Receive rate \(Mbps\)\s*:\s*(.+)$",
        "transmit_rate_mbps": r"^\s*Transmit rate \(Mbps\)\s*:\s*(.+)$",
        "profile": r"^\s*Profile\s*:\s*(.+)$",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.MULTILINE)
        value = m.group(1).strip() if m else None
        data[key] = value

    signal_raw = data.get("signal")
    if isinstance(signal_raw, str) and signal_raw.endswith("%"):
        data["signal_percent"] = int(signal_raw.replace("%", "").strip())
    else:
        data["signal_percent"] = None

    rssi_raw = data.get("rssi")
    try:
        data["rssi_dbm"] = int(str(rssi_raw).strip()) if rssi_raw is not None else None
    except ValueError:
        data["rssi_dbm"] = None

    for field in ["channel", "receive_rate_mbps", "transmit_rate_mbps"]:
        raw = data.get(field)
        try:
            data[field] = int(str(raw).strip()) if raw is not None else None
        except ValueError:
            pass

    return data


def parse_ping_info(text: str) -> Dict[str, Any]:
    ping_data = {
        "packet_loss_percent": None,
        "min_ms": None,
        "max_ms": None,
        "avg_ms": None,
    }

    loss_match = re.search(r"Lost = \d+ \((\d+)% loss\)", text)
    if loss_match:
        ping_data["packet_loss_percent"] = int(loss_match.group(1))

    rtt_match = re.search(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", text)
    if rtt_match:
        ping_data["min_ms"] = int(rtt_match.group(1))
        ping_data["max_ms"] = int(rtt_match.group(2))
        ping_data["avg_ms"] = int(rtt_match.group(3))

    return ping_data
