# Runbook: Dead Letter Queue (DLQ) Overflow

| Field         | Value                              |
|---------------|------------------------------------|
| **Severity**  | P2 (High)                          |
| **Ownership** | Platform / Messaging Team          |
| **Last Updated** | 2026-03-12                      |

---

## 1. Symptoms

- **Metric**: `dlq_messages_total` counter is spiking rapidly.
- **Threshold**: DLQ size exceeds **5 000** messages.
- **Observable behaviour**: Agents report `MessageRouteError` in logs; tasks are silently dropped from the normal processing pipeline and accumulate in the DLQ.
- **Alerts**: Grafana panel "DLQ Depth" shows sustained increase; PagerDuty fires `COS_AA_DLQ_OVERFLOW` alert.

---

## 2. Diagnosis

### 2.1 Check DLQ Length

```bash
# Current DLQ depth
redis-cli -h $REDIS_HOST -p $REDIS_PORT LLEN cos_aa:dlq
```

A healthy system keeps this under **100**. Values above **1 000** indicate a developing problem; above **5 000** is an active incident.

### 2.2 Inspect Recent DLQ Entries

```bash
# View the 6 most-recent dead-lettered messages (newest first)
redis-cli -h $REDIS_HOST -p $REDIS_PORT LRANGE cos_aa:dlq 0 5
```

Look for patterns in the payload:

- **Repeated `agent_id`** -- a single agent is consistently failing.
- **Repeated `tool_name`** -- a specific tool integration is down (check the [Circuit Breaker Open](circuit-breaker-open.md) runbook).
- **Repeated `error_code`** -- a systemic issue (e.g., schema validation, serialization).

### 2.3 Check Circuit Breaker State

```bash
redis-cli -h $REDIS_HOST -p $REDIS_PORT HGETALL cos_aa:circuit_breakers
```

If any breaker is `OPEN`, messages destined for that tool will be dead-lettered until the breaker resets.

### 2.4 Check DLQ Consumer Health

```bash
# Kubernetes
kubectl get pods -l app=cos-aa-dlq-consumer -n cos-aa
kubectl logs -l app=cos-aa-dlq-consumer -n cos-aa --tail=100

# Docker Compose
docker compose -f docker-compose.dev.yml logs --tail=100 dlq-consumer
```

Verify the consumer is running, not in CrashLoopBackOff, and is actively processing messages.

---

## 3. Resolution

### 3.1 Scale DLQ Consumer

If the consumer cannot keep up with the inflow rate:

```bash
# Kubernetes -- scale to 3 replicas
kubectl scale deployment cos-aa-dlq-consumer --replicas=3 -n cos-aa

# Docker Compose
docker compose -f docker-compose.dev.yml up -d --scale dlq-consumer=3
```

### 3.2 Investigate and Fix Root Cause

| Root Cause | Action |
|------------|--------|
| Circuit breaker open for a tool | Follow the [Circuit Breaker Open](circuit-breaker-open.md) runbook. |
| Agent repeatedly crashing | Follow the [Agent Heartbeat Failure](agent-heartbeat-failure.md) runbook. |
| Schema/serialization error | Check recent deployments; roll back if a bad schema was deployed. |
| Redis memory pressure | Increase Redis `maxmemory`; evict stale keys. |

### 3.3 Replay Dead-Lettered Messages

Once the root cause is resolved, replay recoverable messages:

```bash
# Replay DLQ messages back into the main queue (built-in CLI command)
python -m src.messaging.dlq replay --batch-size 500 --delay-ms 50
```

### 3.4 Purge Unrecoverable Messages

If messages are irrecoverably corrupted or obsolete:

```bash
# Archive then purge
redis-cli -h $REDIS_HOST -p $REDIS_PORT RENAME cos_aa:dlq cos_aa:dlq:archived:$(date +%s)

# Or delete outright (destructive)
redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL cos_aa:dlq
```

---

## 4. Prevention

### 4.1 Alert Thresholds

| Threshold | Severity | Action |
|-----------|----------|--------|
| DLQ > 1 000 | Warning (P3) | Investigate during business hours. |
| DLQ > 5 000 | High (P2) | Page on-call; begin diagnosis. |
| DLQ > 8 000 | Critical (P1) | All-hands; risk of Redis memory exhaustion. |

### 4.2 Auto-Scaling

Configure the Horizontal Pod Autoscaler for the DLQ consumer:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cos-aa-dlq-consumer-hpa
  namespace: cos-aa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cos-aa-dlq-consumer
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: External
      external:
        metric:
          name: dlq_messages_total
        target:
          type: Value
          value: "1000"
```

### 4.3 DLQ TTL

Set a TTL on DLQ messages to prevent unbounded growth for very old entries:

```bash
# Trim DLQ to most recent 10 000 entries
redis-cli -h $REDIS_HOST -p $REDIS_PORT LTRIM cos_aa:dlq 0 9999
```

---

## 5. Escalation

If the DLQ continues to grow after scaling consumers and addressing the root cause, escalate to the **Platform Lead** and **SRE on-call**. If Redis memory usage exceeds 80%, coordinate an emergency Redis scale-up.
