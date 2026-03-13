# Runbook: HUB Leader Failover

| Field         | Value                              |
|---------------|------------------------------------|
| **Severity**  | P1 (Critical)                      |
| **Ownership** | Platform / HUB Team                |
| **Last Updated** | 2026-03-12                      |

---

## 1. Symptoms

- **Metric**: `hub_ooda_cycles_total` stops incrementing -- no new OODA cycles are being processed.
- **Metric**: `hub_leader_renewal_failures_total` increases -- the current leader cannot renew its lock.
- **Logs**: `LeaderRenewalFailed` or `LeaderElectionTimeout` in HUB service logs.
- **User impact**: The entire OODA loop stalls. Agents continue running existing tasks but receive no new directives. System appears "frozen."

---

## 2. Diagnosis

### 2.1 Check Current Leader

```bash
# Who holds the leader lock?
redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:hub:leader

# What is the TTL on the lock?
redis-cli -h $REDIS_HOST -p $REDIS_PORT TTL cos_aa:hub:leader
```

- **Key exists with valid TTL**: A leader is active. Check if that instance is healthy (step 2.2).
- **Key exists with TTL = -1**: Lock was set without expiry (bug). Needs manual deletion.
- **Key missing (nil)**: No leader. Election should happen automatically; if it does not, check all HUB instances (step 2.3).

### 2.2 Verify Leader Instance Health

```bash
# Identify the leader instance (value of the key is the instance ID)
LEADER_ID=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:hub:leader)
echo "Current leader: $LEADER_ID"

# Kubernetes -- check if the leader pod is running
kubectl get pods -l app=cos-aa-hub -n cos-aa
kubectl logs <leader-pod-name> -n cos-aa --tail=100
```

Look for:

- Pod in `CrashLoopBackOff` or `Error` state.
- Redis connectivity errors in logs.
- High CPU/memory that could prevent timely lock renewal.

### 2.3 Check All HUB Instances

```bash
# List all HUB replicas
kubectl get pods -l app=cos-aa-hub -n cos-aa -o wide

# Check if any instance is attempting election
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=50 | grep -i "election\|leader"
```

If all instances report `LeaderElectionTimeout`, Redis connectivity may be the issue.

### 2.4 Check Redis Health

```bash
redis-cli -h $REDIS_HOST -p $REDIS_PORT PING
redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO server | grep uptime
redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO clients | grep connected_clients
```

If Redis is unreachable, see the [Redis Failover DR Drill](../dr-drills/redis-failover.md).

---

## 3. Resolution

### 3.1 Force Release Leader Lock

If the current leader is unhealthy and not releasing the lock naturally:

```bash
# Delete the leader key to allow a new election
redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL cos_aa:hub:leader
```

A healthy HUB instance should acquire the lock within **5 seconds** (the election poll interval).

### 3.2 Restart Unhealthy HUB Instances

```bash
# Kill the stale leader pod (Kubernetes will recreate it)
kubectl delete pod <leader-pod-name> -n cos-aa

# Or restart the entire HUB deployment
kubectl rollout restart deployment cos-aa-hub -n cos-aa
```

### 3.3 Verify New Leader Acquired

```bash
# Wait a few seconds, then check
sleep 10
redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:hub:leader
redis-cli -h $REDIS_HOST -p $REDIS_PORT TTL cos_aa:hub:leader
```

The key should exist with a TTL of approximately 15 seconds (the lock duration). The new leader should begin processing OODA cycles immediately.

### 3.4 Verify OODA Processing Resumed

```bash
# Check that cycles are incrementing again
# Query Prometheus or check logs
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=20 | grep "ooda_cycle"
```

---

## 4. Prevention

### 4.1 Leader Lock Configuration

Ensure the leader lock is configured with safe defaults:

```python
# src/hub/leader_election.py (recommended settings)
LEADER_LOCK_KEY = "cos_aa:hub:leader"
LEADER_LOCK_TTL_SECONDS = 15       # Lock auto-expires after 15s
LEADER_RENEWAL_INTERVAL = 5        # Renew every 5s (must be < TTL)
ELECTION_POLL_INTERVAL = 5         # Check for leader vacancy every 5s
MAX_RENEWAL_FAILURES = 3           # Step down after 3 consecutive failures
```

### 4.2 Multiple HUB Replicas

Always run at least **2 HUB instances** in production so that a standby can immediately assume leadership:

```bash
kubectl scale deployment cos-aa-hub --replicas=3 -n cos-aa
```

### 4.3 Alerting

| Condition | Severity | Action |
|-----------|----------|--------|
| Leader renewal failed 1x | Warning | Log only. |
| Leader renewal failed 3x consecutively | P1 (Critical) | Page on-call immediately. |
| No leader for > 30s | P1 (Critical) | Page on-call; OODA loop is stalled. |

### 4.4 Graceful Shutdown

Ensure HUB instances release the leader lock on graceful shutdown:

```python
async def shutdown(self):
    if self.is_leader:
        await self.redis.delete(LEADER_LOCK_KEY)
        logger.info("Released leader lock on shutdown")
```

Configure Kubernetes `terminationGracePeriodSeconds` to allow time for this:

```yaml
terminationGracePeriodSeconds: 30
```

---

## 5. Escalation

Leader failover that does not self-heal within 60 seconds is a **P1 incident**. Escalate to the **Platform Lead** and **SRE on-call**. If the issue is caused by Redis instability, coordinate with the **Infrastructure Team** and execute the [Redis Failover DR Drill](../dr-drills/redis-failover.md).
