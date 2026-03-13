"""
Knowledge Agent: document retrieval, web search, database querying,
and knowledge synthesis. The primary workhorse for information tasks.
"""
from __future__ import annotations

import time
from typing import Any, ClassVar
from uuid import UUID

from src.agents.base_agent import BaseAgent
from src.core.domain_objects import AgentType, ExecutionContext
from src.core.message_schemas import TaskDispatchPayload, TaskResultPayload
from src.llm.embeddings import get_llm_client
from src.memory.memory_service import memory_service
from src.tools.web_search import web_search_tool
from src.tools.file_io import file_io_tool
from src.tools.database_query import database_query_tool

KNOWLEDGE_SYSTEM_PROMPT = """You are a Knowledge Agent in the COS-AA system.
Your job is to find, retrieve, and synthesize information from multiple sources
to answer questions or gather facts needed for decision-making.

When answering, always:
1. Cite your sources (memory, web search, database, documents)
2. Indicate confidence level (high/medium/low)
3. Flag any contradictions between sources
4. Distinguish between factual findings and inferences

Respond in JSON:
{
  "answer": "synthesized answer",
  "confidence": "high|medium|low",
  "sources": [
    {"type": "memory|web|database|document", "reference": "...", "relevance": 0.0-1.0}
  ],
  "contradictions": ["..."],
  "follow_up_suggestions": ["..."]
}
"""


class KnowledgeAgent(BaseAgent):
    agent_type: ClassVar[AgentType] = AgentType.KNOWLEDGE
    supported_task_types: ClassVar[list[str]] = [
        "knowledge_retrieval",
        "document_search",
        "web_search",
        "database_query",
        "knowledge_synthesis",
        "question_answering",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._llm = get_llm_client()
        self.register_tool(web_search_tool)
        self.register_tool(file_io_tool)
        self.register_tool(database_query_tool)

    async def execute_task(
        self, task: TaskDispatchPayload
    ) -> TaskResultPayload:
        start = time.perf_counter()
        self._current_task_count += 1

        try:
            query = task.input_data.get("query", "")
            task_type = task.task_type
            tenant_id = task.input_data.get("tenant_id", str(task.session_id))

            context = ExecutionContext(
                tenant_id=UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
                session_id=task.session_id,
            )

            # Gather information from available sources
            gathered_sources: list[dict[str, Any]] = []

            # 1. Search semantic memory
            try:
                memory_results = await memory_service.retrieve_context(
                    tenant_id=tenant_id,
                    session_id=str(task.session_id),
                    query=query,
                    top_k=5,
                )
                for mem in memory_results.get("semantic", []):
                    gathered_sources.append(
                        {
                            "type": "memory",
                            "content": mem.get("content", ""),
                            "relevance": mem.get("relevance_score", 0.0),
                        }
                    )
            except Exception:
                pass

            # 2. Web search if requested or needed
            if task_type in ("web_search", "knowledge_retrieval", "question_answering"):
                web_result = await self._run_tool(
                    "web_search", {"query": query, "max_results": 5}, context
                )
                if web_result.success and web_result.output:
                    for r in web_result.output.get("results", []):
                        gathered_sources.append(
                            {
                                "type": "web",
                                "content": r.get("content", ""),
                                "url": r.get("url", ""),
                                "relevance": r.get("score", 0.0),
                            }
                        )

            # 3. Database query if specifically requested
            if task_type == "database_query":
                sql = task.input_data.get("sql", "")
                if sql:
                    db_result = await self._run_tool(
                        "database_query", {"query": sql}, context
                    )
                    if db_result.success and db_result.output:
                        gathered_sources.append(
                            {
                                "type": "database",
                                "content": str(db_result.output.get("rows", [])),
                                "row_count": db_result.output.get("row_count", 0),
                                "relevance": 1.0,
                            }
                        )

            # 4. Synthesize with LLM
            user_prompt = f"""Query: {query}

Gathered sources ({len(gathered_sources)} total):
{gathered_sources}

Synthesize an answer from these sources."""

            llm_response = await self._llm.chat_completion_json(
                system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )

            elapsed = (time.perf_counter() - start) * 1000
            return TaskResultPayload(
                task_id=task.task_id,
                success=True,
                output=llm_response.content,
                duration_ms=elapsed,
                tokens_consumed=llm_response.usage.get("total_tokens", 0),
                tool_calls_made=len(gathered_sources),
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return TaskResultPayload(
                task_id=task.task_id,
                success=False,
                output={"error": str(e)},
                duration_ms=elapsed,
            )
        finally:
            self._current_task_count -= 1


knowledge_agent = KnowledgeAgent()
