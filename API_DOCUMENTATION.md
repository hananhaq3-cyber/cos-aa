# 🚀 COS-AA API Documentation

**Status**: ✅ **PRODUCTION READY**
**Version**: 2.0.0
**Base URL**: `https://cos-aa-production.up.railway.app`

---

## API Overview

| Component | Status | Notes |
|-----------|--------|-------|
| **Authentication** | ✅ Working | JWT-based, Argon2 password hashing |
| **Sessions (OODA)** | ✅ Working | Create sessions, send messages, manage state |
| **Agents** | ✅ Available | List, spawn, approve, reject agents |
| **Admin** | ✅ Working | Quotas management, API key generation |
| **Memory** | ✅ Available | Semantic & episodic memory search |
| **Observability** | ✅ Available | Traces, CoT audit trail, health check |
| **CORS** | ✅ Working | Allows `*.vercel.app` domains |
| **Databases** | ✅ Working | PostgreSQL 16.1 + Redis 7.0 |

---

## Authentication

### 1. Register (Signup)

```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "tenant_name": "My Organization"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "email": "user@example.com",
  "role": "admin",
  "expires_in": 3600
}
```

**Error Responses**:
- `409 Conflict`: Email already registered
- `409 Conflict`: Organization name already taken
- `422 Unprocessable Entity`: Invalid email format or missing fields

---

### 2. Login

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response** (200 OK): Same as register response

**Error Responses**:
- `401 Unauthorized`: Invalid email or password
- `404 Not Found`: User does not exist

---

## Sessions (OODA Loop)

### 1. Create Session

```bash
POST /api/v1/sessions
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "goal": "Help me plan a marketing campaign"
}
```

**Response** (201 Created):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "CREATED",
  "created_at": "2026-03-14T12:00:00Z"
}
```

---

### 2. Send Message (Trigger OODA Cycle)

```bash
POST /api/v1/sessions/{session_id}/messages
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "content": "I need help understanding the target market"
}
```

**Response** (200 OK):
```json
{
  "cycle_number": 1,
  "goal_achieved": false,
  "evidence": "Gathered initial market research data",
  "phase": "REVIEWING",
  "duration_ms": 2543.2
}
```

---

### 3. Get Session State

```bash
GET /api/v1/sessions/{session_id}/state
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "ACTIVE",
  "current_phase": "DECIDING",
  "cycle_count": 5,
  "goal": "Help me plan a marketing campaign",
  "created_at": "2026-03-14T12:00:00Z",
  "last_activity": "2026-03-14T12:15:00Z"
}
```

---

## Agents

### 1. List Available Agents

```bash
GET /api/v1/agents
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `status` (optional): Filter by status (e.g., "ACTIVE", "VALIDATING")

**Response** (200 OK):
```json
{
  "agent_types": [
    {
      "definition_id": "550e8400-e29b-41d4-a716-446655440000",
      "agent_type_name": "ResearchAgent",
      "purpose": "Conducts market research for campaigns",
      "status": "ACTIVE",
      "created_at": "2026-03-10T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 2. Spawn New Agent

```bash
POST /api/v1/agents/spawn
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "gap_description": "Need an agent that can analyze competitor pricing",
  "sample_task_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "require_approval": true
}
```

**Response** (201 Created):
```json
{
  "definition_id": "550e8400-e29b-41d4-a716-446655440001",
  "agent_type_name": "CompetitorAnalysisAgent",
  "status": "VALIDATING",
  "message": "Agent spawned successfully, awaiting approval"
}
```

---

## Admin Features

### 1. Get Usage Quotas

```bash
GET /api/v1/admin/quotas
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "quotas": [
    {
      "resource": "OODA Cycles / day",
      "used": 12,
      "limit": 5000
    },
    {
      "resource": "LLM Tokens / day",
      "used": 45000,
      "limit": 5000000
    },
    {
      "resource": "Memory Fragments",
      "used": 150,
      "limit": 100000
    },
    {
      "resource": "Agent Spawns / month",
      "used": 2,
      "limit": 50
    },
    {
      "resource": "API Requests / hour",
      "used": 342,
      "limit": 1000
    },
    {
      "resource": "Storage (MB)",
      "used": 25,
      "limit": 5000
    }
  ]
}
```

---

### 2. Generate API Key

```bash
POST /api/v1/admin/keys
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Response** (201 Created):
```json
{
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "raw_key": "cos-aa_1ef5a79b3c8f0e1d2a3b4c5d6e7f8a9b",
  "created_at": "2026-03-14T12:00:00Z"
}
```

**Note**: Save the `raw_key` immediately - it won't be shown again!

---

### 3. List API Keys

```bash
GET /api/v1/admin/keys
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "keys": [
    {
      "key_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-03-14T12:00:00Z",
      "last_used": "2026-03-14T12:15:00Z",
      "masked": "cos-aa_****...****9b"
    }
  ]
}
```

---

### 4. Revoke API Key

```bash
DELETE /api/v1/admin/keys/{key_id}
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "revoked": true
}
```

---

## Memory System

### Search Memory

```bash
POST /api/v1/memory/search
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "marketing strategies for tech startups",
  "top_k": 10,
  "tiers": ["semantic", "episodic"]
}
```

**Response** (200 OK):
```json
{
  "query": "marketing strategies for tech startups",
  "results": [
    {
      "fragment_id": "550e8400-e29b-41d4-a716-446655440000",
      "tier": "semantic",
      "content": "Product-led growth is effective for tech products...",
      "summary": "PLG strategy overview",
      "relevance_score": 0.95,
      "source_type": "session",
      "tags": ["marketing", "strategy", "tech"]
    }
  ],
  "total": 1,
  "retrieval_latency_ms": 145.3
}
```

---

## Observability

### Get Traces

```bash
GET /api/v1/observability/traces/{trace_id}
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "entries": [
    {
      "id": "entry-1",
      "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "cycle_id": "cycle-1",
      "phase": "OBSERVE",
      "cot_chain": {...},
      "created_at": "2026-03-14T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

### Health Check

```bash
GET /api/v1/observability/health
```

**Response** (200 OK):
```json
{
  "status": "healthy"
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Invalid/missing token |
| 409 | Conflict | Duplicate email/org name |
| 422 | Unprocessable | Invalid email format |
| 500 | Server Error | Internal error |

---

## Rate Limiting

- **API Requests**: 1000 per hour
- **OODA Cycles**: 5000 per day
- **LLM Tokens**: 5,000,000 per day
- **Agent Spawns**: 50 per month

---

## Security

### JWT Token Format

Tokens use **HS256** algorithm with:
- **Expiry**: 60 minutes
- **Claims**: `sub` (user_id), `tenant_id`, `role`, `scopes`

### Password Security

- **Algorithm**: Argon2 (OWASP recommended)
- **No Byte Limit**: Unlike bcrypt, supports any length
- **Salt**: Included automatically

### CORS

Allowed origins:
- `https://cos-aa.vercel.app`
- `https://*.vercel.app` (all Vercel preview deployments)
- Development: all origins (indicated by regex: `.*\.vercel\.app`)

---

## Example: Complete Flow

```bash
# 1. Register
curl -X POST https://cos-aa-production.up.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"demo@example.com",
    "password":"Password123",
    "tenant_name":"Demo Company"
  }'

# Response includes: access_token, user_id, tenant_id

# 2. Create Session
curl -X POST https://cos-aa-production.up.railway.app/api/v1/sessions \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"goal":"Help me plan my project"}'

# Response includes: session_id

# 3. Send Message
curl -X POST https://cos-aa-production.up.railway.app/api/v1/sessions/{session_id}/messages \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"content":"Tell me the first step"}'

# Response shows OODA cycle results

# 4. Check State
curl -X GET https://cos-aa-production.up.railway.app/api/v1/sessions/{session_id}/state \
  -H "Authorization: Bearer {access_token}"

# Shows session progress
```

---

## Support

For issues or questions about the API:
- Check this documentation
- Review /api/v1/observability/health endpoint
- Check admin quotas at /api/v1/admin/quotas

---

**Last Updated**: March 14, 2026
**API Version**: 2.0.0
**Status**: Production Ready ✅
