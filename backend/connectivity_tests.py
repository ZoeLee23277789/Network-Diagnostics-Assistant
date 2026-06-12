from __future__ import annotations

import html
import json
import re
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "location": "local_lab",
    "environment": "windows_fae_test",
    "ping_targets": ["8.8.8.8", "google.com"],
    "dns_targets": ["google.com"],
    "traceroute_target": "google.com",
    "port_targets": [
        {"host": "google.com", "port": 443, "name": "Public HTTPS"},
        {"host": "mqtt.eclipseprojects.io", "port": 8883, "name": "MQTT TLS"},
    ],
    "run_traceroute": True,
    "run_speedtest": False,
}


def run_command(command: list[str], timeout: int = 20) -> dict:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:
        return {
            "success": False,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "stdout": "",
            "stderr": str(exc),
        }


def parse_ping_output(output: str) -> dict:
    loss = None
    avg_ms = None

    loss_match = re.search(r"\((\d+)% loss\)", output, re.IGNORECASE)
    if loss_match:
        loss = int(loss_match.group(1))

    avg_match = re.search(r"Average = (\d+)ms", output, re.IGNORECASE)
    if avg_match:
        avg_ms = int(avg_match.group(1))

    if loss is None:
        loss_match = re.search(r"(\d+(?:\.\d+)?)% packet loss", output, re.IGNORECASE)
        if loss_match:
            loss = float(loss_match.group(1))

    return {"packet_loss_percent": loss, "avg_latency_ms": avg_ms}


def make_test(name: str, category: str, passed: bool, details: dict, recommendation: str = "") -> dict:
    return {
        "name": name,
        "category": category,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "details": details,
        "recommendation": recommendation,
    }


def check_ip_config() -> dict:
    result = run_command(["ipconfig", "/all"], timeout=12)
    output = result["stdout"]
    has_ipv4 = bool(re.search(r"IPv4 Address[^\n:]*:\s*([0-9.]+)", output))
    has_gateway = bool(re.search(r"Default Gateway[^\n:]*:\s*([0-9.]+)", output))
    passed = result["success"] and has_ipv4 and has_gateway

    return make_test(
        "IP configuration",
        "local_network",
        passed,
        {
            "has_ipv4": has_ipv4,
            "has_default_gateway": has_gateway,
            "raw_output": output[:5000],
        },
        "Check DHCP/static IP settings and default gateway if this fails.",
    )


def check_wifi_info() -> dict:
    result = run_command(["netsh", "wlan", "show", "interfaces"], timeout=10)
    output = result["stdout"]
    connected = "State" in output and re.search(r"State\s*:\s*connected", output, re.IGNORECASE)
    signal_match = re.search(r"Signal\s*:\s*(\d+)%", output, re.IGNORECASE)
    signal = int(signal_match.group(1)) if signal_match else None
    passed = result["success"] and bool(connected)

    return make_test(
        "Wi-Fi interface",
        "local_network",
        passed,
        {
            "connected": bool(connected),
            "signal_percent": signal,
            "raw_output": output[:3000],
        },
        "Connect to Wi-Fi or verify the wireless adapter if this fails.",
    )


def check_ping(target: str) -> dict:
    result = run_command(["ping", "-n", "4", target], timeout=18)
    metrics = parse_ping_output(result["stdout"])
    passed = result["success"] and metrics.get("packet_loss_percent") in (0, 0.0)

    return make_test(
        f"Ping {target}",
        "reachability",
        passed,
        {
            "target": target,
            **metrics,
            "raw_output": result["stdout"][:3000],
        },
        "Check gateway, DNS, firewall, VPN, or WAN path if ping fails.",
    )


def check_dns(domain: str) -> dict:
    started = time.perf_counter()
    addresses = []
    error = ""
    try:
        infos = socket.getaddrinfo(domain, None)
        addresses = sorted({item[4][0] for item in infos})
    except Exception as exc:
        error = str(exc)

    nslookup = run_command(["nslookup", domain], timeout=10)
    passed = bool(addresses)

    return make_test(
        f"DNS resolve {domain}",
        "dns",
        passed,
        {
            "domain": domain,
            "resolved_ips": addresses,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": error,
            "raw_output": nslookup["stdout"][:3000],
        },
        "Check DNS server, captive portal, VPN DNS policy, or domain spelling if this fails.",
    )


def check_tcp_port(host: str, port: int, name: str | None = None) -> dict:
    started = time.perf_counter()
    error = ""
    try:
        with socket.create_connection((host, int(port)), timeout=6):
            passed = True
    except Exception as exc:
        passed = False
        error = str(exc)

    return make_test(
        name or f"TCP {host}:{port}",
        "tcp_port",
        passed,
        {
            "host": host,
            "port": int(port),
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": error,
        },
        "Check endpoint hostname, port, firewall, proxy, VPN, or cloud service allowlist if this fails.",
    )


def check_traceroute(target: str) -> dict:
    result = run_command(["tracert", "-d", "-h", "12", target], timeout=35)
    passed = result["success"]
    return make_test(
        f"Traceroute {target}",
        "path",
        passed,
        {"target": target, "raw_output": result["stdout"][:5000], "stderr": result["stderr"]},
        "Use traceroute output to identify where the WAN path stops responding.",
    )


def check_speedtest() -> dict:
    result = run_command(["speedtest", "--format=json"], timeout=90)
    passed = result["success"]
    details = {"raw_output": result["stdout"][:5000], "stderr": result["stderr"]}
    try:
        data = json.loads(result["stdout"])
        details["download_mbps"] = round(data.get("download", {}).get("bandwidth", 0) * 8 / 1_000_000, 2)
        details["upload_mbps"] = round(data.get("upload", {}).get("bandwidth", 0) * 8 / 1_000_000, 2)
        details["latency_ms"] = data.get("ping", {}).get("latency")
    except Exception:
        pass

    return make_test(
        "Speedtest throughput",
        "throughput",
        passed,
        details,
        "Install Ookla Speedtest CLI or skip this optional test if unavailable.",
    )


def summarize_results(tests: list[dict]) -> dict:
    total = len(tests)
    failed = [item for item in tests if not item["passed"]]
    critical_categories = {"local_network", "dns", "reachability", "tcp_port"}
    critical_failed = [item for item in failed if item["category"] in critical_categories]

    if critical_failed:
        overall_status = "fail"
    elif failed:
        overall_status = "warning"
    else:
        overall_status = "pass"

    return {
        "overall_status": overall_status,
        "total_tests": total,
        "passed": total - len(failed),
        "failed": len(failed),
        "failed_tests": [item["name"] for item in failed],
    }


def generate_html_report(report: dict) -> str:
    rows = []
    for test in report["tests"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(test['name'])}</td>"
            f"<td>{html.escape(test['category'])}</td>"
            f"<td>{html.escape(test['status'].upper())}</td>"
            f"<td>{html.escape(test.get('recommendation', ''))}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Connectivity Test Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #102a43; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef7ff; }}
  </style>
</head>
<body>
  <h1>Connectivity Test Report</h1>
  <p><strong>Status:</strong> {html.escape(report['summary']['overall_status'].upper())}</p>
  <p><strong>Timestamp:</strong> {html.escape(report['timestamp'])}</p>
  <p><strong>Passed:</strong> {report['summary']['passed']} / {report['summary']['total_tests']}</p>
  <table>
    <thead><tr><th>Test</th><th>Category</th><th>Status</th><th>Recommended Next Step</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>"""


def save_report(report: dict) -> dict:
    json_path = REPORT_DIR / "latest_report.json"
    html_path = REPORT_DIR / "latest_report.html"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(generate_html_report(report))

    return {"json_report": str(json_path), "html_report": str(html_path)}


def run_connectivity_suite(config: dict | None = None) -> dict:
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    timestamp = datetime.now().isoformat(timespec="seconds")
    tests = [check_ip_config(), check_wifi_info()]

    for target in cfg.get("ping_targets", []):
        tests.append(check_ping(target))

    for domain in cfg.get("dns_targets", []):
        tests.append(check_dns(domain))

    for target in cfg.get("port_targets", []):
        tests.append(check_tcp_port(target["host"], target["port"], target.get("name")))

    if cfg.get("run_traceroute"):
        tests.append(check_traceroute(cfg.get("traceroute_target", "google.com")))

    if cfg.get("run_speedtest"):
        tests.append(check_speedtest())

    report = {
        "timestamp": timestamp,
        "location": cfg.get("location"),
        "environment": cfg.get("environment"),
        "summary": summarize_results(tests),
        "tests": tests,
        "config": cfg,
    }
    report["reports"] = save_report(report)
    return report


def load_latest_report() -> dict | None:
    path = REPORT_DIR / "latest_report.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
