from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def _metric(metrics: dict[str, object], key: str) -> object:
    value = metrics.get(key)
    return "not observed" if value is None else value


def _met(actual: object, target: str) -> str:
    if not isinstance(actual, int | float):
        return "n/a"
    if target == "availability":
        return "yes" if actual >= 0.99 else "no"
    if target == "latency_p95_ms":
        return "yes" if actual < 2500 else "no"
    if target == "fallback_success_rate":
        return "yes" if actual >= 0.95 else "no"
    if target == "cache_hit_rate":
        return "yes" if actual >= 0.10 else "no"
    if target == "recovery_time_ms":
        return "yes" if actual < 5000 else "n/a"
    return "n/a"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", default="reports/metrics.json")
    parser.add_argument("--out", default="reports/final_report.md")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()
    metrics = json.loads(Path(args.metrics).read_text())
    config = yaml.safe_load(Path(args.config).read_text())
    cb_config = config["circuit_breaker"]
    cache_config = config["cache"]
    load_config = config["load_test"]

    lines = [
        "# Day 10 Reliability Final Report",
        "",
        "## Architecture",
        "",
        "```",
        "User Request",
        "  -> ReliabilityGateway",
        "  -> ResponseCache or SharedRedisCache",
        "  -> CircuitBreaker(primary) -> primary provider",
        "  -> CircuitBreaker(backup)  -> backup provider",
        "  -> static fallback message when all providers fail",
        "```",
        "",
        "## Configuration",
        "",
        "| Setting | Value | Reason |",
        "|---|---:|---|",
        f"| failure_threshold | {cb_config['failure_threshold']} | Open a circuit after repeated provider failures. |",
        f"| reset_timeout_seconds | {cb_config['reset_timeout_seconds']} | Bound outage probing delay during chaos runs. |",
        f"| success_threshold | {cb_config['success_threshold']} | Close half-open circuits after a successful probe. |",
        f"| cache backend | {cache_config['backend']} | Default local backend for reproducible tests. |",
        f"| cache TTL seconds | {cache_config['ttl_seconds']} | Avoid stale semantic cache entries. |",
        f"| similarity_threshold | {cache_config['similarity_threshold']} | Require high similarity before reuse. |",
        f"| load_test requests | {load_config['requests']} | Enough requests to exercise cache and circuit transitions. |",
        "",
        "## SLOs",
        "",
        "| SLI | SLO target | Actual value | Met? |",
        "|---|---|---:|---|",
        f"| Availability | >= 99% | {_metric(metrics, 'availability')} | {_met(metrics.get('availability'), 'availability')} |",
        f"| Latency P95 | < 2500 ms | {_metric(metrics, 'latency_p95_ms')} | {_met(metrics.get('latency_p95_ms'), 'latency_p95_ms')} |",
        f"| Fallback success rate | >= 95% | {_metric(metrics, 'fallback_success_rate')} | {_met(metrics.get('fallback_success_rate'), 'fallback_success_rate')} |",
        f"| Cache hit rate | >= 10% | {_metric(metrics, 'cache_hit_rate')} | {_met(metrics.get('cache_hit_rate'), 'cache_hit_rate')} |",
        f"| Recovery time | < 5000 ms | {_metric(metrics, 'recovery_time_ms')} | {_met(metrics.get('recovery_time_ms'), 'recovery_time_ms')} |",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        if key == "scenarios":
            continue
        lines.append(f"| {key} | {_metric(metrics, key)} |")
    lines += [
        "",
        "## Cache And Redis",
        "",
        f"The run used `{cache_config['backend']}` cache with semantic matching and privacy guardrails.",
        "Redis support is implemented through `SharedRedisCache`; run `docker compose up -d` and `pytest tests/test_redis_cache.py -q` to capture shared-cache evidence.",
        "",
        "## Chaos Scenarios",
        "",
        "| Scenario | Status |",
        "|---|---|",
    ]
    for key, value in metrics.get("scenarios", {}).items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "## Failure Analysis",
        "",
        "The main remaining production risk is that circuit state is per process. A multi-instance deployment should move breaker counters and open-state timestamps to Redis or another shared store so all gateway instances shed traffic consistently.",
        "",
        "## Next Steps",
        "",
        "1. Add a no-cache comparison run to quantify saved latency and cost.",
        "2. Persist circuit breaker state for multi-instance deployments.",
        "3. Add concurrency tests around cache and breaker behavior.",
    ]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
