"""
File I/O tool for reading documents (PDF, DOCX, TXT, CSV, JSON).
Supports tenant-scoped file paths to enforce isolation.
Circuit breaker: fail_max=5, reset_timeout=30s. Retry: 1 (no extra attempts).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import ClassVar

from pybreaker import CircuitBreaker, CircuitBreakerError

from src.agents.base_agent import BaseTool
from src.core.domain_objects import ExecutionContext, ToolResult

logger = logging.getLogger(__name__)

_file_io_breaker = CircuitBreaker(fail_max=5, reset_timeout=30)


class FileIOTool(BaseTool):
    tool_name: ClassVar[str] = "file_io"
    tool_type: ClassVar[str] = "FILE_IO"
    required_permissions: ClassVar[list[str]] = ["tool:file_io"]
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "list"],
                "description": "File operation to perform",
            },
            "path": {"type": "string", "description": "File path"},
            "content": {
                "type": "string",
                "description": "Content to write (for write action)",
            },
        },
        "required": ["action", "path"],
    }

    MAX_READ_SIZE = 1_000_000  # 1MB

    async def execute(
        self, input_data: dict, context: ExecutionContext
    ) -> ToolResult:
        action = input_data["action"]
        file_path = input_data["path"]

        start = time.perf_counter()

        # Enforce tenant-scoped paths
        safe_base = Path(f"/data/tenants/{context.tenant_id}")
        resolved = (safe_base / file_path).resolve()
        if not str(resolved).startswith(str(safe_base.resolve())):
            return ToolResult(
                success=False,
                error_message="Path traversal blocked: access denied",
                duration_ms=0.0,
            )

        try:
            return await _file_io_breaker.call_async(
                self._dispatch_action, action, resolved, input_data, start
            )
        except CircuitBreakerError:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("File I/O circuit breaker is OPEN")
            return ToolResult(
                success=False,
                error_message="File I/O circuit breaker is open — too many recent failures",
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                error_message=f"File I/O error: {str(e)}",
                duration_ms=elapsed,
            )

    async def _dispatch_action(
        self, action: str, resolved: Path, input_data: dict, start: float
    ) -> ToolResult:
        if action == "read":
            return await self._read(resolved, start)
        elif action == "write":
            content = input_data.get("content", "")
            return await self._write(resolved, content, start)
        elif action == "list":
            return await self._list(resolved, start)
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown action: {action}",
                duration_ms=0.0,
            )

    async def _read(self, path: Path, start: float) -> ToolResult:
        if not path.exists():
            return ToolResult(
                success=False,
                error_message=f"File not found: {path.name}",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        size = path.stat().st_size
        if size > self.MAX_READ_SIZE:
            return ToolResult(
                success=False,
                error_message=f"File too large: {size} bytes (max {self.MAX_READ_SIZE})",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        suffix = path.suffix.lower()

        if suffix in (".txt", ".md", ".csv", ".log"):
            content = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".json":
            raw = path.read_text(encoding="utf-8")
            content = json.dumps(json.loads(raw), indent=2)
        elif suffix == ".pdf":
            content = await self._read_pdf(path)
        elif suffix == ".docx":
            content = await self._read_docx(path)
        else:
            content = path.read_text(encoding="utf-8", errors="replace")

        elapsed = (time.perf_counter() - start) * 1000
        return ToolResult(
            success=True,
            output={"content": content, "size_bytes": size, "path": path.name},
            duration_ms=elapsed,
        )

    async def _write(
        self, path: Path, content: str, start: float
    ) -> ToolResult:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        elapsed = (time.perf_counter() - start) * 1000
        return ToolResult(
            success=True,
            output={"path": path.name, "bytes_written": len(content.encode())},
            duration_ms=elapsed,
        )

    async def _list(self, path: Path, start: float) -> ToolResult:
        if not path.is_dir():
            return ToolResult(
                success=False,
                error_message=f"Not a directory: {path.name}",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        entries = [
            {"name": p.name, "is_dir": p.is_dir(), "size": p.stat().st_size}
            for p in sorted(path.iterdir())
        ]
        elapsed = (time.perf_counter() - start) * 1000
        return ToolResult(
            success=True, output={"entries": entries}, duration_ms=elapsed
        )

    async def _read_pdf(self, path: Path) -> str:
        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n--- Page Break ---\n\n".join(pages)
        except ImportError:
            return "[pypdf not installed — cannot read PDF files]"

    async def _read_docx(self, path: Path) -> str:
        try:
            import docx

            doc = docx.Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return "[python-docx not installed — cannot read DOCX files]"


file_io_tool = FileIOTool()
