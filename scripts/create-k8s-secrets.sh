#!/usr/bin/env bash
# ─── Create Kubernetes Secrets for COS-AA ───
# Run after EKS cluster is provisioned and kubectl is configured.
# Reads values from environment variables or prompts interactively.
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"

echo "==> Creating COS-AA Kubernetes secrets in namespace: $NAMESPACE"

# Require all secrets to be set as env vars
: "${POSTGRES_URL:?Set POSTGRES_URL env var (e.g. postgresql+asyncpg://user:pass@host:5432/cos_aa)}"
: "${REDIS_URL:?Set REDIS_URL env var (e.g. redis://host:6379/0)}"
: "${CELERY_BROKER_URL:?Set CELERY_BROKER_URL env var (e.g. redis://host:6379/1)}"
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY env var}"
: "${JWT_SECRET_KEY:?Set JWT_SECRET_KEY env var (generate with: openssl rand -hex 32)}"
: "${PINECONE_API_KEY:?Set PINECONE_API_KEY env var}"

kubectl create secret generic cos-aa-secrets \
  --namespace "$NAMESPACE" \
  --from-literal=postgres-url="$POSTGRES_URL" \
  --from-literal=redis-url="$REDIS_URL" \
  --from-literal=celery-broker-url="$CELERY_BROKER_URL" \
  --from-literal=openai-api-key="$OPENAI_API_KEY" \
  --from-literal=jwt-secret-key="$JWT_SECRET_KEY" \
  --from-literal=pinecone-api-key="$PINECONE_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "==> Creating GHCR pull secret"
: "${GITHUB_TOKEN:?Set GITHUB_TOKEN env var (PAT with read:packages scope)}"
: "${GITHUB_USERNAME:?Set GITHUB_USERNAME env var}"

kubectl create secret docker-registry ghcr-pull-secret \
  --namespace "$NAMESPACE" \
  --docker-server=ghcr.io \
  --docker-username="$GITHUB_USERNAME" \
  --docker-password="$GITHUB_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "==> Secrets created. Verify with: kubectl get secrets -n $NAMESPACE"
