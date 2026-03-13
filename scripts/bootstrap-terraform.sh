#!/usr/bin/env bash
# ─── Bootstrap Terraform Remote State ───
# Run this ONCE before the first `terraform init`.
# Creates the S3 bucket + DynamoDB table that store Terraform state.
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
BUCKET_NAME="cos-aa-terraform-state"
DYNAMODB_TABLE="cos-aa-terraform-locks"

echo "==> Creating S3 bucket: $BUCKET_NAME"
aws s3api create-bucket \
  --bucket "$BUCKET_NAME" \
  --region "$AWS_REGION" \
  --create-bucket-configuration LocationConstraint="$AWS_REGION" 2>/dev/null || true

aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "==> Creating DynamoDB table: $DYNAMODB_TABLE"
aws dynamodb create-table \
  --table-name "$DYNAMODB_TABLE" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$AWS_REGION" 2>/dev/null || true

echo "==> Done. You can now run: cd infra/terraform && terraform init"
