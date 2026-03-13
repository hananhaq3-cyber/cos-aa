"""
Tool registry: central catalog for registering, looking up, and listing tools.
"""
from __future__ import annotations

from src.agents.base_agent import BaseTool
from src.core.domain_objects import ToolSpec


class ToolRegistry:
    """Singleton registry of all tools available in the system."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.tool_name] = tool

    def get(self, tool_name: str) -> BaseTool | None:
        return self._tools.get(tool_name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def list_tool_specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                tool_name=t.tool_name,
                tool_type=getattr(t, "tool_type", "CUSTOM"),
                permissions_required=t.required_permissions,
            )
            for t in self._tools.values()
        ]

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def unregister(self, tool_name: str) -> None:
        self._tools.pop(tool_name, None)


tool_registry = ToolRegistry()
