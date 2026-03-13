"""
Database query tool: read-only SQL queries against tenant-scoped PostgreSQL data.
Circuit breaker: fail_max=5, reset_timeout=30s. Retry: 2 attempts.
"""
from __future__ import annotations

import logging
import time
from typing import Any, ClassVar

from pybreaker import CircuitBreaker, CircuitBreakerError
from sqlalchemy import text
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.agents.base_agent import BaseTool
from src.core.domain_objects import ExecutionContext, ToolResult
from src.db.postgres import async_session_factory

logger = logging.getLogger(__name__)

_db_query_breaker = CircuitBreaker(fail_max=5, reset_timeout=30)


class DatabaseQueryTool(BaseTool):
    tool_name: ClassVar[str] = "database_query"
    tool_type: ClassVar[str] = "DATABASE"
    required_permissions: ClassVar[list[str]] = ["tool:database_query"]
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL SELECT query to execute",
            },
            "max_rows": {
                "type": "integer",
                "default": 100,
                "description": "Maximum rows to return",
            },
        },
        "required": ["query"],
    }

    BLOCKED_KEYWORDS = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
    }

    async def execute(
        self, input_data: dict, context: ExecutionContext
    ) -> ToolResult:
        query = input_data["query"].strip()
        max_rows = min(input_data.get("max_rows", 100), 1000)

        start = time.perf_counter()

        # Block write operations
        upper_query = query.upper()
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in upper_query.split():
                elapsed = (time.perf_counter() - start) * 1000
                return ToolResult(
                    success=False,
                    error_message=f"Write operation blocked: {keyword} not allowed",
                    duration_ms=elapsed,
                )

        try:
            data, columns = await self._run_query(query, max_rows, context)
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=True,
                output={
                    "columns": columns,
                    "rows": data,
                    "row_count": len(data),
                    "truncated": len(data) == max_rows,
                },
                duration_ms=elapsed,
            )
        except CircuitBreakerError:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("Database query circuit breaker is OPEN")
            return ToolResult(
                success=False,
                error_message="Database circuit breaker is open — too many recent failures",
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                error_message=f"Database query failed: {str(e)}",
                duration_ms=elapsed,
            )

    @staticmethod
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=0.5, max=5),
        retry=retry_if_exception_type((ConnectionError, OSError)),
        reraise=True,
    )
    async def _run_query(
        query: str, max_rows: int, context: ExecutionContext
    ) -> tuple[list[dict], list[str]]:
        async def _do() -> tuple[list[dict], list[str]]:
            async with async_session_factory() as session:
                await session.execute(
                    text("SET app.tenant_id = :tid"),
                    {"tid": str(context.tenant_id)},
                )
                result = await session.execute(text(query))
                rows = result.fetchmany(max_rows)
                columns = list(result.keys()) if result.keys() else []
                data = [dict(zip(columns, row)) for row in rows]
                return data, columns

        return await _db_query_breaker.call_async(_do)


database_query_tool = DatabaseQueryTool()
