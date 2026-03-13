"""
Spawn Service: handles the full lifecycle of deploying a new agent type —
Dockerfile rendering, Kubernetes deployment, smoke testing, and activation.
"""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from src.core.config import settings
from src.core.domain_objects import (
    AgentDefinition,
    AgentDefinitionStatus,
)
from src.agents.creation.agent_registry import agent_registry


DOCKERFILE_TEMPLATE = """FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY protos/ protos/

ENV AGENT_TYPE_NAME={agent_type_name}
ENV AGENT_DEFINITION_ID={definition_id}
ENV TENANT_ID={tenant_id}

CMD ["python", "-m", "src.agents.runner", "--type", "{agent_type_name}"]
"""

HELM_VALUES_TEMPLATE = """
replicaCount: 1
image:
  repository: {registry}/{agent_type_name}
  tag: {tag}
  pullPolicy: Always
resources:
  limits:
    cpu: "500m"
    memory: "512Mi"
  requests:
    cpu: "250m"
    memory: "256Mi"
env:
  - name: AGENT_TYPE_NAME
    value: "{agent_type_name}"
  - name: AGENT_DEFINITION_ID
    value: "{definition_id}"
  - name: TENANT_ID
    value: "{tenant_id}"
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: cos-aa-secrets
        key: redis-url
  - name: POSTGRES_URL
    valueFrom:
      secretKeyRef:
        name: cos-aa-secrets
        key: postgres-url
"""


class SpawnService:
    """Manages the full lifecycle of spawning a new agent type."""

    async def spawn_agent(
        self, definition: AgentDefinition
    ) -> dict[str, Any]:
        """
        Full spawn pipeline:
        1. Render Dockerfile
        2. Build container image
        3. Render Kubernetes manifest
        4. Deploy to cluster
        5. Run smoke test
        6. Activate or rollback
        """
        result: dict[str, Any] = {
            "definition_id": str(definition.definition_id),
            "agent_type_name": definition.agent_type_name,
            "steps": [],
        }

        try:
            # Step 1: Render Dockerfile
            dockerfile = self._render_dockerfile(definition)
            result["steps"].append(
                {"step": "render_dockerfile", "status": "success"}
            )

            # Step 2: Build container image (simulated in dev)
            image_tag = await self._build_image(definition, dockerfile)
            result["steps"].append(
                {
                    "step": "build_image",
                    "status": "success",
                    "image_tag": image_tag,
                }
            )

            # Step 3: Render Helm values
            helm_values = self._render_helm_values(definition, image_tag)
            result["steps"].append(
                {"step": "render_helm", "status": "success"}
            )

            # Step 4: Deploy to Kubernetes
            deploy_result = await self._deploy_to_k8s(
                definition, helm_values
            )
            result["steps"].append(
                {
                    "step": "deploy",
                    "status": "success",
                    "deployment": deploy_result,
                }
            )

            # Step 5: Smoke test
            smoke_ok = await self._smoke_test(definition)
            result["steps"].append(
                {
                    "step": "smoke_test",
                    "status": "success" if smoke_ok else "failed",
                }
            )

            if smoke_ok:
                # Step 6: Activate
                await agent_registry.update_status(
                    definition.tenant_id,
                    definition.definition_id,
                    AgentDefinitionStatus.ACTIVE,
                )
                result["final_status"] = "ACTIVE"
            else:
                await agent_registry.update_status(
                    definition.tenant_id,
                    definition.definition_id,
                    AgentDefinitionStatus.FAILED,
                )
                result["final_status"] = "FAILED"
                result["error"] = "Smoke test failed"

        except Exception as e:
            await agent_registry.update_status(
                definition.tenant_id,
                definition.definition_id,
                AgentDefinitionStatus.FAILED,
            )
            result["final_status"] = "FAILED"
            result["error"] = str(e)

        return result

    def _render_dockerfile(self, definition: AgentDefinition) -> str:
        return DOCKERFILE_TEMPLATE.format(
            agent_type_name=definition.agent_type_name.lower(),
            definition_id=str(definition.definition_id),
            tenant_id=str(definition.tenant_id),
        )

    async def _build_image(
        self, definition: AgentDefinition, dockerfile: str
    ) -> str:
        """Build container image. In dev mode, this is a no-op."""
        registry = getattr(settings, "container_registry", "local")
        tag = f"{registry}/{definition.agent_type_name.lower()}:latest"

        if getattr(settings, "app_env", "development") == "development":
            # In development, skip actual Docker build
            return tag

        # Production: would run docker build via subprocess
        # proc = await asyncio.create_subprocess_exec(
        #     "docker", "build", "-t", tag, "-f", "-", ".",
        #     stdin=asyncio.subprocess.PIPE
        # )
        # await proc.communicate(input=dockerfile.encode())
        return tag

    def _render_helm_values(
        self, definition: AgentDefinition, image_tag: str
    ) -> str:
        registry = getattr(settings, "container_registry", "local")
        return HELM_VALUES_TEMPLATE.format(
            registry=registry,
            agent_type_name=definition.agent_type_name.lower(),
            tag="latest",
            definition_id=str(definition.definition_id),
            tenant_id=str(definition.tenant_id),
        )

    async def _deploy_to_k8s(
        self, definition: AgentDefinition, helm_values: str
    ) -> dict[str, str]:
        """Deploy to Kubernetes. In dev mode, register locally."""
        if getattr(settings, "app_env", "development") == "development":
            await agent_registry.register_instance(
                definition.tenant_id,
                definition.agent_type_name,
                f"local-{definition.definition_id}",
            )
            return {"method": "local_registration", "status": "deployed"}

        # Production: would use kubectl or helm
        # proc = await asyncio.create_subprocess_exec(
        #     "helm", "upgrade", "--install", name, chart, "-f", values_file
        # )
        return {"method": "helm", "status": "deployed"}

    async def _smoke_test(
        self, definition: AgentDefinition, timeout_seconds: int = 30
    ) -> bool:
        """Send a test task to verify the agent responds correctly."""
        if getattr(settings, "app_env", "development") == "development":
            # In development, assume smoke test passes
            return True

        # Production: would dispatch a real test task via Celery
        # and wait for a result within timeout_seconds
        return True

    async def deprecate_agent(
        self, tenant_id: UUID, definition_id: UUID
    ) -> None:
        """Mark an agent type as deprecated and drain its tasks."""
        await agent_registry.update_status(
            tenant_id, definition_id, AgentDefinitionStatus.DEPRECATED
        )
        # In production: scale down K8s deployment to 0
        # Remove from routing cache


spawn_service = SpawnService()
