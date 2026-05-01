from __future__ import annotations
import re
from typing import Dict, Any


def parse_wifi_info(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    patterns = {
        "adapter": r"^\s*Description\s*:\s*(.+)$",
        "ssid": r"^\s*SSID\s*:\s*(.+)$",
        "ap_bssid": r"^\s*AP BSSID\s*:\s*(.+)$",
        "band": r"^\s*Band\s*:\s*(.+)$",
        "channel": r"^\s*Channel\s*:\s*(.+)$",
        "radio_type": r"^\s*Radio type\s*:\s*(.+)$",
        "authentication": r"^\s*Authentication\s*:\s*(.+)$",
        "cipher": r"^\s*Cipher\s*:\s*(.+)$",
        "signal": r"^\s*Signal\s*:\s*(.+)$",
        "rssi": r"^\s*Rssi\s*:\s*(.+)$",
        "receive_rate_mbps": r"^\s*Receive rate \(Mbps\)\s*:\s*(.+)$",
        "transmit_rate_mbps": r"^\s*Transmit rate \(Mbps\)\s*:\s*(.+)$",
        "profile": r"^\s*Profile\s*:\s*(.+)$",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.MULTILINE)
        data[key] = m.group(1).strip() if m else None

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
            data[field] = None

    return data


def parse_ping_info(text: str) -> Dict[str, Any]:
    ping_data = {
        "target": "8.8.8.8",
        "packet_loss_percent": None,
        "min_ms": None,
        "max_ms": None,
        "avg_ms": None,
        "status": "unknown",
    }

    loss_match = re.search(r"Lost = \d+ \((\d+)% loss\)", text)
    if loss_match:
        ping_data["packet_loss_percent"] = int(loss_match.group(1))

    rtt_match = re.search(
        r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms",
        text,
    )
    if rtt_match:
        ping_data["min_ms"] = int(rtt_match.group(1))
        ping_data["max_ms"] = int(rtt_match.group(2))
        ping_data["avg_ms"] = int(rtt_match.group(3))

    if ping_data["packet_loss_percent"] == 0:
        ping_data["status"] = "success"
    elif ping_data["packet_loss_percent"] is not None:
        ping_data["status"] = "degraded"

    return ping_data


def parse_nslookup_info(text: str) -> Dict[str, Any]:
    dns_data = {
        "dns_server": None,
        "dns_server_ip": None,
        "query": "google.com",
        "resolved_ips": [],
        "status": "unknown",
    }

    server_match = re.search(r"Server:\s+(.+)", text)
    if server_match:
        dns_data["dns_server"] = server_match.group(1).strip()

    address_match = re.search(r"Address:\s+(.+)", text)
    if address_match:
        dns_data["dns_server_ip"] = address_match.group(1).strip()

    # Capture IPv4 and IPv6 addresses after "Addresses:"
    ip_matches = re.findall(
        r"(?:(?:\d{1,3}\.){3}\d{1,3}|[0-9a-fA-F:]{3,})",
        text,
    )

    # Remove DNS server IP if it appears in matches
    cleaned = []
    for ip in ip_matches:
        if ip != dns_data["dns_server_ip"] and ip not in cleaned:
            cleaned.append(ip)

    dns_data["resolved_ips"] = cleaned
    dns_data["status"] = "success" if cleaned else "failed"

    return dns_data