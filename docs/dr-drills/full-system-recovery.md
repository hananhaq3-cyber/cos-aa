# DR Drill: Full System Recovery

| Field         | Value                              |
|---------------|------------------------------------|
| **Frequency** | Semi-annually                      |
| **Duration**  | 60 -- 120 minutes                  |
| **Ownership** | SRE / Platform Team                |
| **Last Drilled** | _TBD_                           |
| **Last Updated** | 2026-03-12                      |

---

## Objective

Validate that the entire COS-AA system can be recovered from a complete outage (all components down) with correct startup ordering, full functionality, and no data loss. This drill simulates a catastrophic failure such as a data-center power loss or a Kubernetes cluster rebuild.

---

## 1. Pre-Drill Checklist

- [ ] **Schedule**: Drill window communicated at least 1 week in advance (longer outage window).
- [ ] **Environment**: Execute in **staging**. Production full-recovery drills require CTO approval.
- [ ] **Backups verified**: Confirm recent backups exist and are restorable.
  ```bash
  # Redis RDB
  ls -la /backups/redis/
  redis-cli -h $REDIS_HOST -p $REDIS_PORT LASTSAVE

  # PostgreSQL
  ls -la /backups/postgres/
  pg_restore --list /backups/postgres/latest.dump | head -20
  ```
- [ ] **Configuration**: All Helm values, environment variables, and secrets are available and current.
- [ ] **Team assembled**: SRE, Platform, Database, and Agent Runtime team members are available.
- [ ] **Communication channel**: Dedicated Slack/Teams channel for drill coordination.
- [ ] **Baseline snapshot**: Record all key metrics before shutting down.

---

## 2. Shutdown Sequence

Shut down components in **reverse dependency order** (dependents first, dependencies last):

```
Agents --> Workers --> HUB --> API --> PostgreSQL --> Redis
```

### Step 1: Stop Agents

```bash
kubectl scale deployment cos-aa-agent --replicas=0 -n cos-aa
kubectl wait --for=delete pod -l app=cos-aa-agent -n cos-aa --timeout=60s
```

### Step 2: Stop Workers (DLQ Consumer, Background Jobs)

```bash
kubectl scale deployment cos-aa-dlq-consumer --replicas=0 -n cos-aa
kubectl scale deployment cos-aa-worker --replicas=0 -n cos-aa
kubectl wait --for=delete pod -l app.kubernetes.io/component=worker -n cos-aa --timeout=60s
```

### Step 3: Stop HUB

```bash
kubectl scale deployment cos-aa-hub --replicas=0 -n cos-aa
kubectl wait --for=delete pod -l app=cos-aa-hub -n cos-aa --timeout=60s
```

### Step 4: Stop API

```bash
kubectl scale deployment cos-aa-api --replicas=0 -n cos-aa
kubectl wait --for=delete pod -l app=cos-aa-api -n cos-aa --timeout=60s
```

### Step 5: Stop PostgreSQL

```bash
# If running in Kubernetes
kubectl scale statefulset cos-aa-postgres --replicas=0 -n cos-aa

# If managed externally
ssh $PG_HOST "sudo systemctl stop patroni && sudo systemctl stop postgresql"
```

### Step 6: Stop Redis

```bash
# If running in Kubernetes
kubectl scale statefulset cos-aa-redis --replicas=0 -n cos-aa

# If managed externally
ssh $REDIS_HOST "sudo systemctl stop redis-sentinel && sudo systemctl stop redis"
```

Verify everything is down:

```bash
kubectl get pods -n cos-aa
# Expected: No pods running
```

Record the shutdown completion time: `_________________`

---

## 3. Recovery Sequence

Start components in **dependency order** (dependencies first, dependents last):

```
Redis --> PostgreSQL --> API --> HUB --> Workers --> Agents
```

### Step 1: Start Redis

```bash
# Kubernetes
kubectl scale statefulset cos-aa-redis --replicas=3 -n cos-aa

# External
ssh $REDIS_HOST "sudo systemctl start redis && sudo systemctl start redis-sentinel"
```

**Verification checklist:**

- [ ] Redis process is running.
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT PING
  # Expected: PONG
  ```
- [ ] Redis data is loaded (check key count).
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT DBSIZE
  ```
- [ ] Sentinel topology is healthy (if using Sentinel).
  ```bash
  redis-cli -h $SENTINEL_HOST -p 26379 SENTINEL masters
  ```
- [ ] Replication is established.
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO replication
  ```

**Estimated time**: 1 -- 3 minutes.

---

### Step 2: Start PostgreSQL

```bash
# Kubernetes
kubectl scale statefulset cos-aa-postgres --replicas=2 -n cos-aa

# External (Patroni)
ssh $PG_HOST "sudo systemctl start patroni"
```

**Verification checklist:**

- [ ] PostgreSQL is accepting connections.
  ```bash
  psql -h $PG_HOST -U cos_aa -d cos_aa -c "SELECT 1;"
  ```
- [ ] Patroni cluster is healthy.
  ```bash
  patronictl -c /etc/patroni/patroni.yml list
  ```
- [ ] Replication is established.
  ```bash
  psql -h $PG_HOST -U cos_aa -d cos_aa -c "SELECT client_addr, state FROM pg_stat_replication;"
  ```
- [ ] Schema is intact.
  ```bash
  psql -h $PG_HOST -U cos_aa -d cos_aa -c "\dt"
  ```
- [ ] Row counts match pre-drill baseline.
  ```bash
  psql -h $PG_HOST -U cos_aa -d cos_aa -c "
  SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;
  "
  ```
- [ ] Run pending Alembic migrations (if any).
  ```bash
  alembic -c alembic.ini upgrade head
  ```

**Estimated time**: 2 -- 5 minutes.

---

### Step 3: Start API

```bash
kubectl scale deployment cos-aa-api --replicas=2 -n cos-aa
kubectl wait --for=condition=ready pod -l app=cos-aa-api -n cos-aa --timeout=120s
```

**Verification checklist:**

- [ ] API pods are Running and Ready.
  ```bash
  kubectl get pods -l app=cos-aa-api -n cos-aa
  ```
- [ ] Health endpoint returns 200.
  ```bash
  curl -s http://cos-aa-api-svc:8000/health | jq .
  ```
- [ ] API can reach Redis.
  ```bash
  curl -s http://cos-aa-api-svc:8000/health/redis | jq .
  ```
- [ ] API can reach PostgreSQL.
  ```bash
  curl -s http://cos-aa-api-svc:8000/health/db | jq .
  ```

**Estimated time**: 1 -- 2 minutes.

---

### Step 4: Start HUB

```bash
kubectl scale deployment cos-aa-hub --replicas=3 -n cos-aa
kubectl wait --for=condition=ready pod -l app=cos-aa-hub -n cos-aa --timeout=120s
```

**Verification checklist:**

- [ ] HUB pods are Running and Ready.
  ```bash
  kubectl get pods -l app=cos-aa-hub -n cos-aa
  ```
- [ ] Leader election succeeded.
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:hub:leader
  redis-cli -h $REDIS_HOST -p $REDIS_PORT TTL cos_aa:hub:leader
  ```
- [ ] HUB state is clean (not stuck from pre-shutdown).
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT GET cos_aa:hub:state
  # If stuck, reset:
  # redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL cos_aa:hub:state
  ```

**Estimated time**: 1 -- 2 minutes.

---

### Step 5: Start Workers

```bash
kubectl scale deployment cos-aa-worker --replicas=2 -n cos-aa
kubectl scale deployment cos-aa-dlq-consumer --replicas=1 -n cos-aa
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=worker -n cos-aa --timeout=120s
```

**Verification checklist:**

- [ ] Worker pods are Running and Ready.
  ```bash
  kubectl get pods -l app.kubernetes.io/component=worker -n cos-aa
  ```
- [ ] DLQ consumer is processing (if DLQ has messages from the outage).
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT LLEN cos_aa:dlq
  ```

**Estimated time**: 1 -- 2 minutes.

---

### Step 6: Start Agents

```bash
kubectl scale deployment cos-aa-agent --replicas=5 -n cos-aa
kubectl wait --for=condition=ready pod -l app=cos-aa-agent -n cos-aa --timeout=120s
```

**Verification checklist:**

- [ ] Agent pods are Running and Ready.
  ```bash
  kubectl get pods -l app=cos-aa-agent -n cos-aa
  ```
- [ ] Agent heartbeats are registering.
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT KEYS "cos_aa:agent:*:heartbeat" | wc -l
  # Expected: matches the number of agent replicas
  ```
- [ ] Agents are accepting tasks.
  ```bash
  kubectl logs -l app=cos-aa-agent -n cos-aa --tail=20 | grep -i "ready\|started\|listening"
  ```

**Estimated time**: 1 -- 3 minutes.

---

## 4. End-to-End Validation

After all components are running, perform a full end-to-end validation:

### 4.1 OODA Cycle Functioning

- [ ] HUB is processing OODA cycles.
  ```bash
  kubectl logs -l app=cos-aa-hub -n cos-aa --tail=20 | grep "ooda_cycle"
  ```
- [ ] Cycle completes all four phases: OBSERVING -> ORIENTING -> DECIDING -> ACTING.

### 4.2 Memory Subsystem

- [ ] Memory write succeeds.
  ```bash
  curl -s -X POST http://cos-aa-api-svc:8000/api/v1/memory \
    -H "Content-Type: application/json" \
    -d '{"agent_id": "drill-test", "content": "DR drill test memory entry", "type": "episodic"}' | jq .
  ```
- [ ] Memory search returns results (including the entry just written).
  ```bash
  curl -s http://cos-aa-api-svc:8000/api/v1/memory/search \
    -H "Content-Type: application/json" \
    -d '{"query": "DR drill test", "agent_id": "drill-test", "limit": 5}' | jq .
  ```

### 4.3 Tool Execution

- [ ] Circuit breakers are all CLOSED.
  ```bash
  redis-cli -h $REDIS_HOST -p $REDIS_PORT HGETALL cos_aa:circuit_breakers
  ```
- [ ] A sample tool call succeeds (e.g., `file_io` or `database_query`).

### 4.4 Metrics and Observability

- [ ] Prometheus is scraping all targets.
  ```bash
  curl -s http://prometheus-svc:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
  ```
- [ ] Grafana dashboards are populating with data.
- [ ] PagerDuty integration is active (send a test alert if needed).

---

## 5. Data Integrity Validation

### 5.1 Redis Data

```bash
# Verify key namespaces exist
redis-cli -h $REDIS_HOST -p $REDIS_PORT KEYS "cos_aa:*" | wc -l

# Spot check critical keys
redis-cli -h $REDIS_HOST -p $REDIS_PORT EXISTS cos_aa:hub:leader
redis-cli -h $REDIS_HOST -p $REDIS_PORT EXISTS cos_aa:circuit_breakers
```

### 5.2 PostgreSQL Data

```bash
# Compare row counts against pre-drill baseline
psql -h $PG_HOST -U cos_aa -d cos_aa -c "
SELECT
  (SELECT COUNT(*) FROM memories) AS memories_count,
  (SELECT COUNT(*) FROM sessions) AS sessions_count,
  (SELECT COUNT(*) FROM ooda_cycles) AS cycles_count,
  (SELECT COUNT(*) FROM agents) AS agents_count;
"
```

### 5.3 No Orphaned State

```bash
# Check for OODA cycles that were in-progress during shutdown
psql -h $PG_HOST -U cos_aa -d cos_aa -c "
SELECT id, status, started_at FROM ooda_cycles WHERE status NOT IN ('COMPLETED', 'FAILED') ORDER BY started_at DESC LIMIT 10;
"
# If found, mark them as FAILED
# UPDATE ooda_cycles SET status = 'FAILED', completed_at = NOW() WHERE status NOT IN ('COMPLETED', 'FAILED');
```

---

## 6. Rollback

If recovery fails at any step, do not proceed to the next step. Instead:

1. **Collect logs** from the failing component.
2. **Check backups** -- if data is corrupted, restore from the pre-drill backup.
3. **Restart from Step 1** of the recovery sequence after fixing the issue.
4. If the drill is in production and recovery is taking too long, invoke the **Major Incident** process.

---

## 7. Post-Drill Report

| Metric | Value |
|--------|-------|
| Total shutdown time | ____m |
| Total recovery time | ____m |
| Redis recovery time | ____m |
| PostgreSQL recovery time | ____m |
| API recovery time | ____m |
| HUB recovery time (including leader election) | ____m |
| Workers recovery time | ____m |
| Agents recovery time (all heartbeats healthy) | ____m |
| First OODA cycle completed after recovery | ____m |
| Data integrity issues | None / Describe |
| DLQ messages from the outage | ____ |
| Drill result | PASS / FAIL |
| Action items | |

---

## 8. Related Resources

- [Redis Failover Drill](redis-failover.md)
- [PostgreSQL Failover Drill](postgres-failover.md)
- [HUB Leader Failover Runbook](../runbooks/hub-leader-failover.md)
- [Agent Heartbeat Failure Runbook](../runbooks/agent-heartbeat-failure.md)
- [DLQ Overflow Runbook](../runbooks/dlq-overflow.md)
- [Circuit Breaker Open Runbook](../runbooks/circuit-breaker-open.md)
