# Day 10 Reliability Final Report

## Architecture

```
User Request
  -> ReliabilityGateway
  -> ResponseCache or SharedRedisCache
  -> CircuitBreaker(primary) -> primary provider
  -> CircuitBreaker(backup)  -> backup provider
  -> static fallback message when all providers fail
```

## Configuration

| Setting | Value | Reason |
|---|---:|---|
| failure_threshold | 3 | Open a circuit after repeated provider failures. |
| reset_timeout_seconds | 2 | Bound outage probing delay during chaos runs. |
| success_threshold | 1 | Close half-open circuits after a successful probe. |
| cache backend | memory | Default local backend for reproducible tests. |
| cache TTL seconds | 300 | Avoid stale semantic cache entries. |
| similarity_threshold | 0.92 | Require high similarity before reuse. |
| load_test requests | 100 | Enough requests to exercise cache and circuit transitions. |

## SLOs

| SLI | SLO target | Actual value | Met? |
|---|---|---:|---|
| Availability | >= 99% | 0.9867 | no |
| Latency P95 | < 2500 ms | 315.25 | yes |
| Fallback success rate | >= 95% | 0.957 | yes |
| Cache hit rate | >= 10% | 0.6133 | yes |
| Recovery time | < 5000 ms | not observed | n/a |

## Metrics

| Metric | Value |
|---|---:|
| total_requests | 300 |
| availability | 0.9867 |
| error_rate | 0.0133 |
| latency_p50_ms | 278.52 |
| latency_p95_ms | 315.25 |
| latency_p99_ms | 318.4 |
| fallback_success_rate | 0.957 |
| cache_hit_rate | 0.6133 |
| circuit_open_count | 12 |
| recovery_time_ms | not observed |
| estimated_cost | 0.04393 |
| estimated_cost_saved | 0.184 |

## Cache And Redis

The run used `memory` cache with semantic matching and privacy guardrails.
Redis support is implemented through `SharedRedisCache`; run `docker compose up -d` and `pytest tests/test_redis_cache.py -q` to capture shared-cache evidence.

## Chaos Scenarios

| Scenario | Status |
|---|---|
| primary_timeout_100 | pass |
| primary_flaky_50 | pass |
| all_healthy | pass |

## Failure Analysis

The main remaining production risk is that circuit state is per process. A multi-instance deployment should move breaker counters and open-state timestamps to Redis or another shared store so all gateway instances shed traffic consistently.

## Next Steps

1. Add a no-cache comparison run to quantify saved latency and cost.
2. Persist circuit breaker state for multi-instance deployments.
3. Add concurrency tests around cache and breaker behavior.