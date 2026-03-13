"""
Web search tool using Tavily API for grounded search results.
Circuit breaker: fail_max=3, reset_timeout=60s. Retry: 2 attempts.
"""
from __future__ import annotations

import logging
import time
from typing import Any, ClassVar

import httpx
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.agents.base_agent import BaseTool
from src.core.config import settings
from src.core.domain_objects import ExecutionContext, ToolResult

logger = logging.getLogger(__name__)

_web_search_breaker = CircuitBreaker(fail_max=3, reset_timeout=60)


class WebSearchTool(BaseTool):
    tool_name: ClassVar[str] = "web_search"
    tool_type: ClassVar[str] = "WEB_SEARCH"
    required_permissions: ClassVar[list[str]] = ["tool:web_search"]
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {
                "type": "integer",
                "default": 5,
                "description": "Maximum results to return",
            },
            "search_depth": {
                "type": "string",
                "enum": ["basic", "advanced"],
                "default": "basic",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self, input_data: dict, context: ExecutionContext
    ) -> ToolResult:
        query = input_data["query"]
        max_results = input_data.get("max_results", 5)
        search_depth = input_data.get("search_depth", "basic")

        start = time.perf_counter()

        api_key = getattr(settings, "tavily_api_key", None)
        if not api_key:
            return ToolResult(
                success=False,
                error_message="TAVILY_API_KEY not configured",
                duration_ms=0.0,
            )

        try:
            data = await self._call_tavily(api_key, query, max_results, search_depth)

            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                }
                for r in data.get("results", [])
            ]

            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=True,
                output={"query": query, "results": results},
                duration_ms=elapsed,
            )
        except CircuitBreakerError:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("Web search circuit breaker is OPEN")
            return ToolResult(
                success=False,
                error_message="Web search circuit breaker is open — too many recent failures",
                duration_ms=elapsed,
            )
        except httpx.HTTPStatusError as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                error_message=f"Tavily API error: {e.response.status_code}",
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                error_message=f"Web search failed: {str(e)}",
                duration_ms=elapsed,
            )

    @staticmethod
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        reraise=True,
    )
    async def _call_tavily(
        api_key: str, query: str, max_results: int, search_depth: str
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await _web_search_breaker.call_async(
                client.post,
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth,
                },
            )
            resp.raise_for_status()
            return resp.json()


web_search_tool = WebSearchTool()
