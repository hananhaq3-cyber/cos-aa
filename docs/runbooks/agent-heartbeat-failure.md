# Runbook: Agent Heartbeat Failure

| Field         | Value                              |
|---------------|------------------------------------|
| **Severity**  | P3 (Medium)                        |
| **Ownership** | Agent Runtime Team                 |
| **Last Updated** | 2026-03-12                      |

---

## 1. Symptoms

- **Metric**: `agent_heartbeat_stale_total` counter increasing -- one or more agents have not sent a heartbeat within the expected interval.
- **Metric**: `agent_respawns_total` spiking -- the heartbeat monitor is repeatedly respawning agents that immediately die again.
- **Logs**: `AgentHeartbeatTimeout` or `AgentRespawnTriggered` entries in the HUB service logs.
- **User impact**: Tasks assigned to the failed agent are not processed; they may eventually be dead-lettered (see [DLQ Overflow](dlq-overflow.md)).

---

## 2. Diagnosis

### 2.1 Identify the Affected Agent(s)

```bash
# List all heartbeat keys and their last-seen timestamps
redis-cli -h $REDIS_HOST -p $REDIS_PORT KEYS "cos_aa:agent:*:heartbeat"

# Check a specific agent's heartbeat
redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:agent:<agent_id>:heartbeat

# Check TTL remaining (heartbeat keys expire after 30s by default)
redis-cli -h $REDIS_HOST -p $REDIS_PORT TTL cos_aa:agent:<agent_id>:heartbeat
```

A missing key or TTL of `-2` means the heartbeat has expired entirely.

### 2.2 Check Agent Pod/Container Status

```bash
# Kubernetes
kubectl get pods -l app=cos-aa-agent -n cos-aa
kubectl describe pod <agent-pod-name> -n cos-aa

# Docker Compose
docker compose -f docker-compose.dev.yml ps | grep agent
docker inspect <agent-container-id> --format '{{.State.Status}} {{.State.ExitCode}}'
```

### 2.3 Check for OOM Kills

```bash
# Kubernetes -- look for OOMKilled in last restart reason
kubectl get pods -l app=cos-aa-agent -n cos-aa -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'

# Docker
docker inspect <agent-container-id> --format '{{.State.OOMKilled}}'
```

### 2.4 Check Agent Logs

```bash
# Kubernetes
kubectl logs <agent-pod-name> -n cos-aa --tail=200 --previous   # previous container if it crashed
kubectl logs <agent-pod-name> -n cos-aa --tail=200               # current container

# Docker Compose
docker compose -f docker-compose.dev.yml logs --tail=200 agent
```

Look for:

- `MemoryError` or `Killed` -- OOM.
- `ConnectionRefusedError` on Redis -- agent cannot reach Redis to send heartbeats.
- `asyncio.TimeoutError` -- event loop is blocked, heartbeat coroutine starved.
- Unhandled exceptions in the agent's task processing loop.

### 2.5 Check Resource Usage

```bash
# Kubernetes
kubectl top pod -l app=cos-aa-agent -n cos-aa

# Docker
docker stats --no-stream $(docker ps -q --filter "name=agent")
```

---

## 3. Resolution

### 3.1 Manual Respawn

If a single agent is stuck, force-kill and let the orchestrator restart it:

```bash
# Kubernetes
kubectl delete pod <agent-pod-name> -n cos-aa

# Docker Compose
docker compose -f docker-compose.dev.yml restart agent
```

### 3.2 Fix Resource Limits (OOM)

If agents are being OOM-killed, increase memory limits:

```yaml
# In Helm values or Kubernetes manifest
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

Apply the change:

```bash
helm upgrade cos-aa infra/helm/cos-aa -f infra/helm/cos-aa/values.yaml -n cos-aa
```

### 3.3 Fix Redis Connectivity

If the agent cannot reach Redis:

```bash
# Verify Redis is reachable from the agent pod
kubectl exec -it <agent-pod-name> -n cos-aa -- redis-cli -h $REDIS_HOST -p $REDIS_PORT PING
```

If Redis is down or unreachable, see the [Redis Failover DR Drill](../dr-drills/redis-failover.md).

### 3.4 Unblock Event Loop

If the heartbeat coroutine is being starved by a long-running synchronous task:

- Check if agents are calling blocking I/O without `await`.
- Ensure CPU-intensive tasks are offloaded to a thread/process pool.
- Increase the heartbeat interval if the workload genuinely requires long synchronous phases (not recommended -- prefer making work async).

---

## 4. Prevention

### 4.1 Resource Requests and Limits

Always set explicit resource `requests` and `limits` for agent pods. Use Vertical Pod Autoscaler (VPA) recommendations to right-size.

### 4.2 Auto-Respawn via Heartbeat Monitor

The HUB heartbeat monitor should be configured to automatically respawn agents:

```python
# src/hub/heartbeat_monitor.py (configuration)
HEARTBEAT_INTERVAL_SECONDS = 10      # Agent sends heartbeat every 10s
HEARTBEAT_TTL_SECONDS = 30           # Key expires after 30s (3 missed beats)
MAX_RESPAWN_ATTEMPTS = 5             # Give up after 5 consecutive respawns
RESPAWN_BACKOFF_BASE_SECONDS = 2     # Exponential backoff: 2, 4, 8, 16, 32s
```

### 4.3 Alerting

| Condition | Severity | Action |
|-----------|----------|--------|
| 1 agent stale > 60s | P3 | Investigate during business hours. |
| 3+ agents stale simultaneously | P2 | Page on-call -- possible systemic issue. |
| `agent_respawns_total` > 10 in 5 min | P2 | Crash loop detected -- escalate. |

### 4.4 Liveness Probes

Ensure Kubernetes liveness probes are configured so the kubelet can restart unresponsive agents independently of the COS-AA heartbeat monitor:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8081
  initialDelaySeconds: 15
  periodSeconds: 10
  failureThreshold: 3
```

---

## 5. Escalation

If agents continue to crash-loop after increasing resources and fixing connectivity, escalate to the **Agent Runtime Lead**. If the issue correlates with a recent deployment, consider an immediate rollback.
