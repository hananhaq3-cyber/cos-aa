# Runbook: Stuck OODA Cycle

| Field         | Value                              |
|---------------|------------------------------------|
| **Severity**  | P2 (High)                          |
| **Ownership** | Platform / HUB Team                |
| **Last Updated** | 2026-03-12                      |

---

## 1. Symptoms

- **Metric**: `hub_ooda_cycle_duration_seconds` exceeds **300 seconds** (5 minutes) for a single cycle.
- **Metric**: `hub_ooda_phase_duration_seconds{phase="<PHASE>"}` shows one phase consuming all the time.
- **Observable state**: `hub_state` in Redis is stuck on one of `OBSERVING`, `ORIENTING`, `DECIDING`, or `ACTING` for an extended period.
- **User impact**: New observations are not being processed; agents may idle or repeat stale tasks.

---

## 2. Diagnosis

### 2.1 Check Current HUB State

```bash
# What phase is the cycle stuck in?
redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:hub:state

# When did this phase start?
redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:hub:phase_started_at
```

### 2.2 Diagnose by Phase

#### OBSERVING (Stuck gathering data)

```bash
# Check if the observation aggregator is blocked
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=100 | grep -i "observ"

# Check agent message queues -- are agents sending observations?
redis-cli -h $REDIS_HOST -p $REDIS_PORT LLEN cos_aa:hub:observations
```

**Common causes**: Agent heartbeat failures (no observations arriving), Redis read timeout, excessively large observation payload.

#### ORIENTING (Stuck analyzing context)

```bash
# Check LLM call latency
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=100 | grep -i "orient\|llm\|latency"

# Check LLM service health
curl -s http://$LLM_SERVICE_HOST:$LLM_SERVICE_PORT/health
```

**Common causes**: LLM provider latency spike or outage, context window overflow, prompt exceeding token limit.

#### DECIDING (Stuck choosing action)

```bash
# Check decision engine logs
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=100 | grep -i "decid\|decision"

# Check if LLM returned an unparseable response
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=100 | grep -i "parse\|json\|schema"
```

**Common causes**: LLM returning malformed JSON, decision validation loop (retrying indefinitely), deadlock in decision conflict resolution.

#### ACTING (Stuck dispatching tasks)

```bash
# Check agent task queues
redis-cli -h $REDIS_HOST -p $REDIS_PORT KEYS "cos_aa:agent:*:tasks"

# Check if agents are accepting tasks
redis-cli -h $REDIS_HOST -p $REDIS_PORT LLEN cos_aa:agent:<agent_id>:tasks
```

**Common causes**: All agents are dead or unresponsive, task queue is full, circuit breaker open on required tool (see [Circuit Breaker Open](circuit-breaker-open.md)).

### 2.3 Check LLM Latency

```bash
# Query Prometheus for recent LLM call durations
curl -s "http://$PROMETHEUS_HOST:9090/api/v1/query?query=histogram_quantile(0.95,rate(llm_request_duration_seconds_bucket[5m]))"
```

If P95 latency exceeds 60 seconds, the LLM provider is likely the bottleneck.

---

## 3. Resolution

### 3.1 Forcefully Fail the Current Cycle

If the cycle is irrecoverably stuck, fail it and let the next cycle begin:

```bash
# Set state to FAILED -- the HUB will start a fresh cycle
redis-cli -h $REDIS_HOST -p $REDIS_PORT SET cos_aa:hub:state "FAILED"

# Clear the stale phase timestamp
redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL cos_aa:hub:phase_started_at
```

Alternatively, use the built-in admin CLI:

```bash
python -m src.hub.admin force-fail-cycle --reason "manual intervention: stuck in <PHASE>"
```

### 3.2 Investigate the Bottleneck Phase

| Phase | Likely Fix |
|-------|-----------|
| OBSERVING | Restart stale agents (see [Agent Heartbeat Failure](agent-heartbeat-failure.md)). |
| ORIENTING | Switch to fallback LLM provider or reduce context size. |
| DECIDING | Fix prompt template; add JSON schema validation with retry limit. |
| ACTING | Restart agents; close/reset circuit breakers on blocked tools. |

### 3.3 Restart the HUB (Last Resort)

```bash
kubectl rollout restart deployment cos-aa-hub -n cos-aa
```

This will release the leader lock and trigger a fresh leader election and cycle.

---

## 4. Prevention

### 4.1 Cycle Timeout

Configure an overall cycle timeout (default: **300 seconds**). If the cycle exceeds this, it is automatically failed:

```python
# src/hub/ooda_loop.py
OODA_CYCLE_TIMEOUT_SECONDS = 300  # 5 minutes total for one full cycle
```

### 4.2 Phase-Level Timeouts

Set individual phase timeouts so that a single slow phase does not consume the entire budget:

```python
# src/hub/ooda_loop.py
PHASE_TIMEOUTS = {
    "OBSERVING": 60,    # 60s to gather observations
    "ORIENTING": 90,    # 90s for LLM-based orientation
    "DECIDING":  60,    # 60s for decision generation
    "ACTING":    90,    # 90s to dispatch and confirm tasks
}
```

### 4.3 LLM Fallback

Configure a fallback LLM provider so that ORIENTING/DECIDING phases can continue even if the primary provider is slow:

```yaml
# config/llm.yaml
providers:
  primary:
    name: openai
    model: gpt-4
    timeout: 60
  fallback:
    name: anthropic
    model: claude-3-sonnet
    timeout: 45
```

### 4.4 Alerting

| Condition | Severity | Action |
|-----------|----------|--------|
| Any phase > 2 minutes | Warning | Log and monitor. |
| Any phase > 4 minutes | P2 (High) | Page on-call. |
| Cycle total > 5 minutes | P2 (High) | Auto-fail cycle; page on-call. |
| 3+ cycles failed in 15 minutes | P1 (Critical) | Systemic issue -- escalate. |

---

## 5. Escalation

If cycles are repeatedly failing or getting stuck, escalate to the **HUB Team Lead**. If the root cause is LLM provider latency, open an incident with the provider and switch to the fallback provider.
