# DR Drill: Redis Failover

| Field         | Value                              |
|---------------|------------------------------------|
| **Frequency** | Quarterly                          |
| **Duration**  | 30 -- 60 minutes                   |
| **Ownership** | SRE / Infrastructure Team          |
| **Last Drilled** | _TBD_                           |
| **Last Updated** | 2026-03-12                      |

---

## Objective

Validate that the COS-AA system can survive a Redis primary failure by:

1. Redis Sentinel promoting a replica to primary.
2. All COS-AA services reconnecting to the new primary.
3. The HUB leader election re-acquiring the leader lock on the new primary.
4. No data loss for in-flight OODA cycles and agent heartbeats.

---

## 1. Pre-Drill Checklist

- [ ] **Schedule**: Drill window communicated to all stakeholders at least 48 hours in advance.
- [ ] **Environment**: Drill is executed in **staging** first. Production drills require VP-level approval.
- [ ] **Monitoring**: Ensure Grafana dashboards and PagerDuty alerting are active so drill effects are visible.
- [ ] **Redis topology confirmed**: At least 1 primary + 2 replicas + 3 Sentinel instances.
  ```bash
  redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL masters
  redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL replicas cos-aa-master
  ```
- [ ] **Backup**: Trigger an RDB snapshot before the drill.
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT BGSAVE
  redis-cli -h $REDIS_HOST -p $REDIS_PORT LASTSAVE
  ```
- [ ] **Application health**: All COS-AA pods are Running, no existing alerts firing.
  ```bash
  kubectl get pods -n cos-aa
  kubectl get events -n cos-aa --sort-by='.lastTimestamp' | tail -20
  ```
- [ ] **Record baseline metrics**: Note current values for `hub_ooda_cycles_total`, `dlq_messages_total`, `agent_heartbeat_stale_total`.

---

## 2. Drill Execution

### Step 1: Identify the Current Primary

```bash
redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL get-master-addr-by-name cos-aa-master
```

Record the IP/port of the current primary: `_________________`

### Step 2: Simulate Primary Failure

**Option A -- Kill the process (preferred for realism):**

```bash
# SSH into the Redis primary node
ssh redis-primary-node

# Kill the Redis process
sudo kill -9 $(pgrep -f "redis-server.*:6379")
```

**Option B -- Network partition (iptables):**

```bash
# Block all traffic to/from the primary on the Redis port
sudo iptables -A INPUT -p tcp --dport 6379 -j DROP
sudo iptables -A OUTPUT -p tcp --sport 6379 -j DROP
```

**Option C -- Sentinel DEBUG command (least disruptive):**

```bash
redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL failover cos-aa-master
```

Record the kill time: `_________________`

### Step 3: Observe Sentinel Failover

```bash
# Watch Sentinel logs (should show +sdown, +odown, +failover-state-*)
redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL masters

# Confirm new primary elected
redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL get-master-addr-by-name cos-aa-master
```

Expected: Sentinel promotes a replica within **10--30 seconds**.

Record the new primary IP/port: `_________________`
Record the failover completion time: `_________________`

### Step 4: Observe COS-AA Reconnection

```bash
# Check HUB logs for reconnection
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=50 | grep -i "redis\|connect\|reconnect"

# Check agent logs
kubectl logs -l app=cos-aa-agent -n cos-aa --tail=50 | grep -i "redis\|connect\|reconnect"

# Check API logs
kubectl logs -l app=cos-aa-api -n cos-aa --tail=50 | grep -i "redis\|connect\|reconnect"
```

Expected: All services reconnect within **30--60 seconds** of failover.

### Step 5: Verify Leader Election Re-Acquires

```bash
# Check that a HUB instance has re-acquired the leader lock on the new primary
redis-cli -h $NEW_REDIS_HOST -p $NEW_REDIS_PORT GET cos_aa:hub:leader
redis-cli -h $NEW_REDIS_HOST -p $NEW_REDIS_PORT TTL cos_aa:hub:leader
```

Expected: Leader lock is held with a valid TTL.

---

## 3. Validation

### 3.1 Functional Checks

- [ ] **OODA cycle resumes**: `hub_ooda_cycles_total` is incrementing.
  ```bash
  kubectl logs -l app=cos-aa-hub -n cos-aa --tail=10 | grep "ooda_cycle"
  ```
- [ ] **Agent heartbeats healthy**: `agent_heartbeat_stale_total` is not increasing.
  ```bash
  redis-cli -h $NEW_REDIS_HOST -p $NEW_REDIS_PORT KEYS "cos_aa:agent:*:heartbeat" | head -5
  ```
- [ ] **DLQ stable**: `dlq_messages_total` did not spike excessively (some DLQ messages during failover window are acceptable).
  ```bash
  redis-cli -h $NEW_REDIS_HOST -p $NEW_REDIS_PORT LLEN cos_aa:dlq
  ```
- [ ] **API responding**: Health endpoint returns 200.
  ```bash
  curl -s http://cos-aa-api-svc:8000/health | jq .
  ```

### 3.2 Data Integrity

- [ ] Circuit breaker states preserved.
  ```bash
  redis-cli -h $NEW_REDIS_HOST -p $NEW_REDIS_PORT HGETALL cos_aa:circuit_breakers
  ```
- [ ] Agent registration data intact.
  ```bash
  redis-cli -h $NEW_REDIS_HOST -p $NEW_REDIS_PORT KEYS "cos_aa:agent:*" | wc -l
  ```

---

## 4. Rollback

If the failover does not complete or the system does not recover:

### 4.1 Restore the Original Primary

```bash
# If using Option A (killed process), restart Redis
ssh redis-primary-node
sudo systemctl start redis

# If using Option B (iptables), remove the rules
sudo iptables -D INPUT -p tcp --dport 6379 -j DROP
sudo iptables -D OUTPUT -p tcp --sport 6379 -j DROP
```

### 4.2 Force Sentinel to Re-Elect Original Primary

```bash
redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL failover cos-aa-master
```

### 4.3 Restart COS-AA Services

If services cannot reconnect:

```bash
kubectl rollout restart deployment cos-aa-hub -n cos-aa
kubectl rollout restart deployment cos-aa-agent -n cos-aa
kubectl rollout restart deployment cos-aa-api -n cos-aa
```

---

## 5. Post-Drill Report

Fill in after the drill:

| Metric | Value |
|--------|-------|
| Failover detection time (Sentinel sdown) | ____s |
| Failover completion time (new primary elected) | ____s |
| COS-AA reconnection time | ____s |
| Leader re-election time | ____s |
| Total downtime (no OODA cycles processed) | ____s |
| DLQ messages generated during failover | ____ |
| Data loss observed | Yes / No |
| Drill result | PASS / FAIL |
| Action items | |

---

## 6. Related Runbooks

- [HUB Leader Failover](../runbooks/hub-leader-failover.md)
- [Agent Heartbeat Failure](../runbooks/agent-heartbeat-failure.md)
- [DLQ Overflow](../runbooks/dlq-overflow.md)
