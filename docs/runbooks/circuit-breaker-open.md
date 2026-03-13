# Runbook: Circuit Breaker Open

| Field         | Value                              |
|---------------|------------------------------------|
| **Severity**  | P2 (High)                          |
| **Ownership** | Platform / Tools Integration Team  |
| **Last Updated** | 2026-03-12                      |

---

## 1. Symptoms

- **Error message**: Agents or tool calls return `CircuitBreakerOpenError: circuit breaker open for <tool_name>`.
- **Metric**: `tool_circuit_breaker_state{tool="<tool_name>"}` is `OPEN`.
- **Metric**: `tool_call_errors_total{tool="<tool_name>"}` spiked shortly before the breaker opened.
- **Downstream effect**: Tasks requiring the affected tool are dead-lettered (see [DLQ Overflow](dlq-overflow.md)). OODA ACTING phase may stall (see [Stuck OODA Cycle](ooda-cycle-stuck.md)).

---

## 2. Diagnosis

### 2.1 Identify Which Breaker(s) Are Open

```bash
# List all circuit breaker states
redis-cli -h $REDIS_HOST -p $REDIS_PORT HGETALL cos_aa:circuit_breakers
```

Output format:

```
1) "web_search"
2) "OPEN"
3) "database_query"
4) "CLOSED"
5) "code_interpreter"
6) "CLOSED"
7) "file_io"
8) "HALF_OPEN"
```

### 2.2 Check When the Breaker Opened

```bash
# Timestamp when the breaker transitioned to OPEN
redis-cli -h $REDIS_HOST -p $REDIS_PORT HGET cos_aa:circuit_breaker_meta <tool_name>:opened_at
```

### 2.3 Check Failure Logs for the Tool

```bash
# Kubernetes
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=200 | grep -i "<tool_name>"

# Look specifically for errors
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=200 | grep -i "<tool_name>.*error\|<tool_name>.*fail\|<tool_name>.*timeout"
```

### 2.4 Check the Underlying Service

| Tool | Health Check |
|------|-------------|
| `web_search` | `curl -s https://api.search-provider.com/health` |
| `database_query` | `psql -h $PG_HOST -U cos_aa -c "SELECT 1"` |
| `code_interpreter` | `curl -s http://code-interpreter-svc:8080/health` |
| `file_io` | `ls -la /data/cos-aa/ && df -h /data/cos-aa/` |

---

## 3. Resolution

### 3.1 Wait for Automatic Reset

Each tool has a configured `reset_timeout` after which the breaker transitions to `HALF_OPEN` and allows a single trial request:

| Tool | `reset_timeout` | Failure Threshold | Success Threshold (to close) |
|------|-----------------|-------------------|------------------------------|
| `web_search` | **60 seconds** | 5 failures in 60s | 3 consecutive successes |
| `database_query` | **30 seconds** | 3 failures in 30s | 2 consecutive successes |
| `code_interpreter` | **120 seconds** | 5 failures in 120s | 3 consecutive successes |
| `file_io` | **30 seconds** | 3 failures in 30s | 2 consecutive successes |

If the underlying service has recovered, the breaker will close automatically after the reset timeout.

### 3.2 Fix the Underlying Service

| Tool | Common Failures | Fix |
|------|----------------|-----|
| `web_search` | API rate limit, DNS failure, provider outage | Wait for rate limit reset; check DNS; switch provider. |
| `database_query` | Connection pool exhausted, PG down, slow queries | Restart PG connection pool; check [Postgres Failover](../dr-drills/postgres-failover.md). |
| `code_interpreter` | Sandbox OOM, container crash | Restart interpreter pods; increase memory limits. |
| `file_io` | Disk full, permission denied, NFS mount stale | Free disk space; fix permissions; remount NFS. |

### 3.3 Manually Reset the Circuit Breaker

If the service is confirmed healthy and you do not want to wait for the automatic reset:

```bash
# Reset a single breaker to CLOSED
redis-cli -h $REDIS_HOST -p $REDIS_PORT HSET cos_aa:circuit_breakers <tool_name> "CLOSED"

# Clear the failure counter
redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL cos_aa:circuit_breaker:<tool_name>:failures
```

Or use the admin CLI:

```bash
python -m src.tools.admin reset-breaker --tool <tool_name>
```

### 3.4 Replay Affected Tasks

After the breaker closes, dead-lettered tasks that failed due to the open breaker can be replayed:

```bash
python -m src.messaging.dlq replay --filter-tool <tool_name> --batch-size 200
```

---

## 4. Prevention

### 4.1 Tuning Thresholds

If a tool is flaky but generally recoverable, consider increasing the failure threshold or shortening the reset timeout:

```python
# src/tools/circuit_breaker.py
CIRCUIT_BREAKER_CONFIG = {
    "web_search": {
        "failure_threshold": 5,
        "reset_timeout": 60,
        "success_threshold": 3,
    },
    "database_query": {
        "failure_threshold": 3,
        "reset_timeout": 30,
        "success_threshold": 2,
    },
    "code_interpreter": {
        "failure_threshold": 5,
        "reset_timeout": 120,
        "success_threshold": 3,
    },
    "file_io": {
        "failure_threshold": 3,
        "reset_timeout": 30,
        "success_threshold": 2,
    },
}
```

### 4.2 Retries Before Breaker

Configure tool-level retries with exponential backoff so that transient errors do not trip the breaker:

```python
# Each tool call retries up to 3 times before counting as a breaker failure
TOOL_RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,   # seconds
    "max_delay": 10.0,
    "backoff_factor": 2,
}
```

### 4.3 Alerting

| Condition | Severity | Action |
|-----------|----------|--------|
| Any breaker enters OPEN | P2 (High) | Page on-call. |
| Breaker OPEN > 5 minutes | P1 (Critical) | Escalate -- prolonged tool outage. |
| Multiple breakers OPEN simultaneously | P1 (Critical) | Systemic issue -- escalate immediately. |

### 4.4 Fallback Tools

Where possible, configure fallback tools so the OODA cycle can continue even when a primary tool's breaker is open:

```yaml
# config/tools.yaml
tools:
  web_search:
    primary: google_search
    fallback: bing_search
  database_query:
    primary: postgres
    fallback: readonly_replica
```

---

## 5. Escalation

If a circuit breaker remains open for more than 10 minutes after manual investigation, escalate to the **Tools Integration Lead** and the team responsible for the underlying service. If multiple breakers are open simultaneously, treat it as a **P1 incident** and engage the **SRE on-call**.
