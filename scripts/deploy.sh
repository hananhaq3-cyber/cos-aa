#!/usr/bin/env bash
# ─── Deploy all COS-AA Helm charts ───
# Usage: ./scripts/deploy.sh <environment>
# Example: ./scripts/deploy.sh staging
set -euo pipefail

ENV="${1:?Usage: $0 <staging|production>}"
HELM_DIR="infra/helm"
TAG="${IMAGE_TAG:-latest}"

if [[ "$ENV" != "staging" && "$ENV" != "production" ]]; then
  echo "Error: environment must be 'staging' or 'production'"
  exit 1
fi

CLUSTER="cos-aa-${ENV}"
echo "==> Configuring kubectl for cluster: $CLUSTER"
aws eks update-kubeconfig --name "$CLUSTER" --region "${AWS_REGION:-us-east-1}"

echo "==> Deploying COS-AA to $ENV (image tag: $TAG)"

# Deploy in dependency order
for chart in cos-aa-api cos-aa-hub cos-aa-agents cos-aa-worker cos-aa-memory cos-aa-frontend; do
  echo "--- Deploying $chart"
  helm upgrade --install "$chart" "$HELM_DIR/$chart" \
    --set image.tag="$TAG" \
    --wait --timeout 5m
done

echo "==> All charts deployed. Checking health..."
kubectl get pods -l app=cos-aa-api -o wide
kubectl get pods -l app=cos-aa-frontend -o wide
echo "==> Done."
