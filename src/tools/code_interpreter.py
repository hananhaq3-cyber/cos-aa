"""
Sandboxed code interpreter tool.
Strategy pattern: subprocess (dev), docker (staging), gvisor (prod).
Circuit breaker: fail_max=3, reset_timeout=120s.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import ClassVar

from pybreaker import CircuitBreaker, CircuitBreakerError

from src.agents.base_agent import BaseTool
from src.core.config import settings
from src.core.domain_objects import ExecutionContext, ToolResult

logger = logging.getLogger(__name__)

_code_breaker = CircuitBreaker(fail_max=3, reset_timeout=120)


class CodeInterpreterTool(BaseTool):
    tool_name: ClassVar[str] = "code_interpreter"
    tool_type: ClassVar[str] = "CODE_INTERPRETER"
    required_permissions: ClassVar[list[str]] = ["tool:code_interpreter"]
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute",
            },
            "timeout_seconds": {
                "type": "integer",
                "default": 30,
                "description": "Maximum execution time",
            },
        },
        "required": ["code"],
    }

    MAX_OUTPUT_CHARS = 10000
    DOCKER_IMAGE = "python:3.11-slim"

    async def execute(
        self, input_data: dict, context: ExecutionContext
    ) -> ToolResult:
        code = input_data["code"]
        timeout = min(input_data.get("timeout_seconds", 30), 60)

        start = time.perf_counter()

        try:
            return await _code_breaker.call_async(
                self._run_code, code, timeout, start
            )
        except CircuitBreakerError:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("Code interpreter circuit breaker is OPEN")
            return ToolResult(
                success=False,
                error_message="Code interpreter circuit breaker is open — too many recent failures",
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                error_message=f"Code interpreter error: {str(e)}",
                duration_ms=elapsed,
            )

    async def _run_code(
        self, code: str, timeout: int, start: float
    ) -> ToolResult:
        backend = settings.sandbox_backend
        if backend == "subprocess":
            return await self._execute_subprocess(code, timeout, start)
        elif backend in ("docker", "gvisor"):
            return await self._execute_docker(
                code, timeout, start, use_gvisor=(backend == "gvisor")
            )
        else:
            return await self._execute_subprocess(code, timeout, start)

    async def _execute_subprocess(
        self, code: str, timeout: int, start: float
    ) -> ToolResult:
        """Development: run code in a local subprocess."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            script_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                elapsed = (time.perf_counter() - start) * 1000
                return ToolResult(
                    success=False,
                    error_message=f"Code execution timed out after {timeout}s",
                    duration_ms=elapsed,
                )

            return self._build_result(stdout, stderr, proc.returncode, start)
        finally:
            Path(script_path).unlink(missing_ok=True)

    async def _execute_docker(
        self, code: str, timeout: int, start: float, use_gvisor: bool = False
    ) -> ToolResult:
        """Production: run code in a Docker container, optionally with gVisor runtime."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            script_path = f.name

        try:
            cmd = [
                "docker", "run", "--rm",
                "--network=none",
                "--memory=256m",
                "--cpus=0.5",
                "-v", f"{script_path}:/app/script.py:ro",
            ]
            if use_gvisor:
                cmd.extend(["--runtime=runsc"])
            cmd.extend([self.DOCKER_IMAGE, "python", "/app/script.py"])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                elapsed = (time.perf_counter() - start) * 1000
                return ToolResult(
                    success=False,
                    error_message=f"Code execution timed out after {timeout}s",
                    duration_ms=elapsed,
                )

            return self._build_result(stdout, stderr, proc.returncode, start)
        finally:
            Path(script_path).unlink(missing_ok=True)

    def _build_result(
        self, stdout: bytes, stderr: bytes, returncode: int, start: float
    ) -> ToolResult:
        elapsed = (time.perf_counter() - start) * 1000
        stdout_text = stdout.decode("utf-8", errors="replace")[: self.MAX_OUTPUT_CHARS]
        stderr_text = stderr.decode("utf-8", errors="replace")[: self.MAX_OUTPUT_CHARS]

        if returncode != 0:
            return ToolResult(
                success=False,
                output={"stdout": stdout_text, "stderr": stderr_text},
                error_message=f"Code exited with return code {returncode}",
                duration_ms=elapsed,
            )

        return ToolResult(
            success=True,
            output={"stdout": stdout_text, "stderr": stderr_text},
            duration_ms=elapsed,
        )


code_interpreter_tool = CodeInterpreterTool()
