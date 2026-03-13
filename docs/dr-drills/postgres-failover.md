# DR Drill: PostgreSQL Failover

| Field         | Value                              |
|---------------|------------------------------------|
| **Frequency** | Quarterly                          |
| **Duration**  | 30 -- 60 minutes                   |
| **Ownership** | SRE / Database Team                |
| **Last Drilled** | _TBD_                           |
| **Last Updated** | 2026-03-12                      |

---

## Objective

Validate that the COS-AA system can survive a PostgreSQL primary failure by:

1. Patroni (or pgpool) promoting a standby replica to primary.
2. Application connection pools reconnecting to the new primary.
3. Memory queries continuing to function correctly.
4. Session state remaining intact with no data loss.

---

## 1. Pre-Drill Checklist

- [ ] **Schedule**: Drill window communicated to all stakeholders at least 48 hours in advance.
- [ ] **Environment**: Execute in **staging** first. Production requires VP-level approval.
- [ ] **Monitoring**: Grafana Postgres dashboards and PagerDuty alerting active.
- [ ] **Cluster topology confirmed**: 1 primary + at least 1 synchronous replica.
  ```bash
  # Patroni
  patronictl -c /etc/patroni/patroni.yml list

  # Or check replication status directly
  psql -h $PG_HOST -U cos_aa -d cos_aa -c "SELECT client_addr, state, sync_state FROM pg_stat_replication;"
  ```
- [ ] **Replication lag**: Confirm lag is near zero before starting.
  ```bash
  psql -h $PG_HOST -U cos_aa -d cos_aa -c "SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;"
  ```
- [ ] **Backup**: Trigger a manual backup before the drill.
  ```bash
  pg_basebackup -h $PG_HOST -U replication -D /backups/pre-drill-$(date +%Y%m%d) -Ft -z -P
  ```
- [ ] **Application health**: All COS-AA pods Running, no existing alerts.
  ```bash
  kubectl get pods -n cos-aa
  ```
- [ ] **Baseline metrics**: Record current values for `db_connections_active`, `memory_query_duration_seconds`, `db_errors_total`.

---

## 2. Drill Execution

### Step 1: Identify the Current Primary

```bash
# Patroni
patronictl -c /etc/patroni/patroni.yml list

# Direct SQL
psql -h $PG_HOST -U cos_aa -d cos_aa -c "SELECT NOT pg_is_in_recovery() AS is_primary;"
```

Record the current primary host: `_________________`

### Step 2: Simulate Primary Failure

**Option A -- Patroni switchover (graceful, recommended for first drill):**

```bash
patronictl -c /etc/patroni/patroni.yml switchover --master $PRIMARY_HOST --candidate $REPLICA_HOST --force
```

**Option B -- Kill the PostgreSQL process (realistic failure):**

```bash
ssh $PRIMARY_HOST
sudo systemctl stop postgresql
# Or: sudo kill -9 $(pgrep -f "postgres.*main")
```

**Option C -- Network partition:**

```bash
ssh $PRIMARY_HOST
sudo iptables -A INPUT -p tcp --dport 5432 -j DROP
sudo iptables -A OUTPUT -p tcp --sport 5432 -j DROP
```

Record the failure injection time: `_________________`

### Step 3: Observe Failover

```bash
# Watch Patroni perform the failover
patronictl -c /etc/patroni/patroni.yml list

# Watch logs
journalctl -u patroni -f --no-pager | head -50
```

Expected: Patroni promotes the replica within **10--30 seconds** (configurable via `ttl` and `loop_wait`).

Record the new primary host: `_________________`
Record the failover completion time: `_________________`

### Step 4: Observe Connection Pool Recovery

```bash
# Check API service logs for connection errors and reconnection
kubectl logs -l app=cos-aa-api -n cos-aa --tail=100 | grep -i "postgres\|pg\|database\|connect\|pool"

# Check HUB logs
kubectl logs -l app=cos-aa-hub -n cos-aa --tail=100 | grep -i "postgres\|pg\|database\|connect\|pool"
```

Expected: SQLAlchemy/asyncpg connection pools detect the failure and reconnect within **30--60 seconds**. Some queries will fail with transient errors during the failover window.

### Step 5: Verify Application-Level Recovery

```bash
# API health check
curl -s http://cos-aa-api-svc:8000/health | jq .

# Verify database connectivity from the API pod
kubectl exec -it $(kubectl get pods -l app=cos-aa-api -n cos-aa -o jsonpath='{.items[0].metadata.name}') -n cos-aa -- python -c "
from src.db.session import get_engine
import asyncio
async def check():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('DB connection OK:', result.scalar())
asyncio.run(check())
"
```

---

## 3. Validation

### 3.1 Memory Queries Still Work

The memory subsystem stores agent episodic and semantic memories in PostgreSQL. Verify these queries still function:

```bash
# Test memory retrieval endpoint
curl -s http://cos-aa-api-svc:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test drill", "agent_id": "agent-001", "limit": 5}' | jq .

# Direct SQL verification
kubectl exec -it $(kubectl get pods -l app=cos-aa-api -n cos-aa -o jsonpath='{.items[0].metadata.name}') -n cos-aa -- psql -h $PG_HOST -U cos_aa -d cos_aa -c "
SELECT id, agent_id, created_at
FROM memories
ORDER BY created_at DESC
LIMIT 5;
"
```

- [ ] Memory search returns results without errors.
- [ ] Memory write (inserting a new memory) succeeds.
- [ ] Vector similarity search (pgvector) returns ranked results.

### 3.2 Session State Intact

```bash
# Verify active sessions are preserved
kubectl exec -it $(kubectl get pods -l app=cos-aa-api -n cos-aa -o jsonpath='{.items[0].metadata.name}') -n cos-aa -- psql -h $PG_HOST -U cos_aa -d cos_aa -c "
SELECT COUNT(*) AS active_sessions FROM sessions WHERE expires_at > NOW();
"

# Verify OODA cycle history
kubectl exec -it $(kubectl get pods -l app=cos-aa-api -n cos-aa -o jsonpath='{.items[0].metadata.name}') -n cos-aa -- psql -h $PG_HOST -U cos_aa -d cos_aa -c "
SELECT id, status, started_at, completed_at
FROM ooda_cycles
ORDER BY started_at DESC
LIMIT 5;
"
```

- [ ] Active session count matches pre-drill count.
- [ ] No orphaned or corrupted cycle records.

### 3.3 Data Integrity

```bash
# Check for replication consistency (run on new primary)
psql -h $NEW_PG_HOST -U cos_aa -d cos_aa -c "
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC
LIMIT 10;
"

# Verify no sequences are out of sync
psql -h $NEW_PG_HOST -U cos_aa -d cos_aa -c "
SELECT sequencename, last_value FROM pg_sequences WHERE schemaname = 'public';
"
```

- [ ] Row counts match pre-drill baseline.
- [ ] No data loss detected.

### 3.4 Connection Pool Metrics

- [ ] `db_connections_active` has recovered to normal levels.
- [ ] `db_errors_total` is no longer increasing.
- [ ] `memory_query_duration_seconds` P95 is back to normal.

---

## 4. Rollback

If the failover does not complete or the system does not recover:

### 4.1 Restore the Original Primary

```bash
# If using Option B (killed process)
ssh $ORIGINAL_PRIMARY_HOST
sudo systemctl start postgresql

# If using Option C (iptables)
ssh $ORIGINAL_PRIMARY_HOST
sudo iptables -D INPUT -p tcp --dport 5432 -j DROP
sudo iptables -D OUTPUT -p tcp --sport 5432 -j DROP
```

### 4.2 Force Patroni Switchback

```bash
patronictl -c /etc/patroni/patroni.yml switchover --master $NEW_PRIMARY --candidate $ORIGINAL_PRIMARY --force
```

### 4.3 Restart Application Connection Pools

If connection pools are in a bad state:

```bash
kubectl rollout restart deployment cos-aa-api -n cos-aa
kubectl rollout restart deployment cos-aa-hub -n cos-aa
```

### 4.4 Point-in-Time Recovery (Worst Case)

If data corruption is detected:

```bash
# Restore from the pre-drill backup
pg_restore -h $PG_HOST -U cos_aa -d cos_aa /backups/pre-drill-$(date +%Y%m%d)
```

---

## 5. Post-Drill Report

| Metric | Value |
|--------|-------|
| Failover detection time | ____s |
| Failover completion time (new primary writable) | ____s |
| Connection pool recovery time | ____s |
| Total write downtime | ____s |
| Memory queries functional after | ____s |
| Sessions lost | ____ |
| Data loss observed | Yes / No |
| Drill result | PASS / FAIL |
| Action items | |

---

## 6. Related Runbooks

- [Full System Recovery](full-system-recovery.md)
- [Stuck OODA Cycle](../runbooks/ooda-cycle-stuck.md)
