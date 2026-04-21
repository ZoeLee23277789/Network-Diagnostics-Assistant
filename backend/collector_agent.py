from __future__ import annotations
import datetime
import json
import os
import subprocess
from typing import Any, Dict
import requests
from parsers import parse_wifi_info, parse_ping_info

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/api/records")


def run_command(cmd: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.stdout.strip()


def collect_data(location: str = "unknown", environment: str = "unknown") -> Dict[str, Any]:
    timestamp = datetime.datetime.now().isoformat()

    speedtest_raw = run_command("speedtest --format=json")
    wifi_raw = run_command("netsh wlan show interfaces")
    ping_raw = run_command("ping 8.8.8.8 -n 10")
    tracert_raw = run_command("tracert google.com")
    nslookup_raw = run_command("nslookup google.com")

    speedtest = json.loads(speedtest_raw)
    wifi = parse_wifi_info(wifi_raw)
    ping = parse_ping_info(ping_raw)

    return {
        "timestamp": timestamp,
        "location": location,
        "environment": environment,
        "speedtest": {
            "download_mbps": round(speedtest["download"]["bandwidth"] * 8 / 1_000_000, 2),
            "upload_mbps": round(speedtest["upload"]["bandwidth"] * 8 / 1_000_000, 2),
            "latency_ms": speedtest["ping"]["latency"],
            "jitter_ms": speedtest["ping"]["jitter"],
            "packet_loss": speedtest.get("packetLoss"),
            "isp": speedtest.get("isp"),
            "server_name": speedtest["server"]["name"],
            "server_location": speedtest["server"]["location"],
            "result_url": speedtest["result"]["url"],
        },
        "wifi": wifi,
        "ping": ping,
        "raw_outputs": {
            "wifi_raw": wifi_raw,
            "ping_raw": ping_raw,
            "tracert_raw": tracert_raw,
            "nslookup_raw": nslookup_raw,
        },
    }


def send_record(record: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(API_URL, json=record, timeout=120)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    location = input("Enter location label (example: library / lab / cafe / home): ").strip() or "unknown"
    environment = input("Enter environment (indoor / outdoor / lab / office): ").strip() or "unknown"
    record = collect_data(location=location, environment=environment)
    result = send_record(record)
    print(json.dumps(result, indent=2, ensure_ascii=False))
