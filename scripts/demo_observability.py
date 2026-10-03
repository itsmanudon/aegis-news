"""Export bounded local observability evidence without credentials or raw log dumps."""

import base64
import json
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts.demo import ROOT, compose_command


def get(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=15) as response:
        value: dict[str, Any] = json.load(response)
        return value


def main() -> None:
    prometheus = get(
        "http://127.0.0.1:39090/api/v1/query?"
        + urllib.parse.urlencode({"query": 'up{job="aegisnews-api"}'})
    )
    assert prometheus["data"]["result"][0]["value"][1] == "1"
    auth = {"Authorization": "Basic " + base64.b64encode(b"aegis_dev:aegis_dev_only").decode()}
    dashboard = get("http://127.0.0.1:33001/api/dashboards/uid/aegis-demo", auth)
    query = '{service="aegisnews"} | json | correlation_id="aegis-demo-v1"'
    logs: list[dict[str, Any]] = []
    for _ in range(12):
        result = get(
            "http://127.0.0.1:33100/loki/api/v1/query_range?"
            + urllib.parse.urlencode(
                {"query": query, "limit": 100, "start": int((time.time() - 3600) * 1e9)}
            )
        )
        for stream in result["data"]["result"]:
            logs.extend(json.loads(line) for _, line in stream["values"])
        if any(log.get("trace_id") for log in logs):
            break
        time.sleep(2)
    samples = [
        {
            key: log.get(key)
            for key in ("message", "logger", "correlation_id", "trace_id", "span_id")
        }
        for log in logs
        if log.get("trace_id")
    ][:8]
    assert samples, "No correlated worker spans in Loki"
    matched_trace = None
    trace_ids = [str(sample["trace_id"]) for sample in samples if sample["trace_id"] is not None]
    for _ in range(12):
        collector = subprocess.check_output(
            compose_command("logs", "--tail", "3000", "otel-collector"), cwd=ROOT, text=True
        )
        matched_trace = next((trace_id for trace_id in trace_ids if trace_id in collector), None)
        if matched_trace:
            break
        time.sleep(2)  # OTel batch exporters flush asynchronously.
    assert matched_trace, "No matching Loki worker trace received by the collector"
    report = {
        "result": "passed",
        "prometheus_api_up": True,
        "grafana_dashboard": dashboard["dashboard"]["title"],
        "loki_correlated_trace_examples": samples,
        "otel_collector_received_spans": True,
        "collector_matched_worker_trace_id": matched_trace,
        "trace_storage_limitation": (
            "Collector debug export only; no trace database/UI. Loki trace IDs and Temporal "
            "tracing preserve context; inspect collector logs for receipt."
        ),
    }
    target: Path = ROOT / ".integration-results/observability.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
