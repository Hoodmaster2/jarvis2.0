"""
Research Agent - performs web searches, summarizes information, gathers and validates sources.
"""
import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are JARVIS Research Agent. Your role is to:
1. Search the web for information using available tools
2. Summarize and organize findings
3. Cross-reference multiple sources
4. Extract key facts and actionable information
5. Identify the credibility of sources

You use the web_search and browser skills to gather information."""


class ResearchAgent(BaseAgent):
    """Web research and information gathering."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = RESEARCH_SYSTEM_PROMPT
        self._research_history: list[dict] = []

    async def execute_task(self, task_data: dict) -> Any:
        action = task_data.get("action", "web_search")
        handlers = {
            "web_search": self._web_search,
            "deep_research": self._deep_research,
            "summarize_findings": self._summarize_findings,
            "extract_facts": self._extract_facts,
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(task_data)

    async def _web_search(self, task_data: dict) -> dict:
        """Search the web for information."""
        query = task_data.get("query", "")
        num_results = task_data.get("num_results", 5)

        # Check if web_search skill is available
        skill = self.skills.get_skill("web_search")
        if skill and skill.enabled:
            result = await self.skills.execute_command("web_search", "search", query=query, num_results=num_results)
            search_results = result.get("results", [])

            # Summarize what was found
            summary = await self._summarize_search_results(query, search_results)
            self._research_history.append({"query": query, "results_count": len(search_results)})
            await self.observe({"type": "web_search", "query": query, "results": len(search_results)})
            return {"query": query, "results": search_results, "summary": summary}
        else:
            return {"error": "web_search skill not available", "query": query}

    async def _deep_research(self, task_data: dict) -> dict:
        """Perform deep research on a topic."""
        topic = task_data.get("topic", "")
        depth = task_data.get("depth", 3)

        # Generate sub-questions for comprehensive research
        prompt = f"""For deep research on '{topic}', generate {depth} specific sub-questions to search for.
Output as JSON array of strings."""

        sub_questions_json = await self.think(prompt)
        import re
        questions_match = re.search(r'\[[\s\S]*\]', sub_questions_json)
        questions = json.loads(questions_match.group()) if questions_match else [topic]

        # Search each question
        all_results = []
        for q in questions[:depth]:
            result = await self._web_search({"query": q, "num_results": 3})
            if "results" in result:
                all_results.extend(result["results"])

        # Compile comprehensive summary
        combined = "\n".join(f"- {r.get('title','')}: {r.get('snippet','')}" for r in all_results)
        summary = await self.think(f"Compile a comprehensive research summary on '{topic}' from these findings:\n{combined[:3000]}")

        return {
            "topic": topic,
            "sub_questions": questions[:depth],
            "total_sources": len(all_results),
            "summary": summary,
            "sources": all_results[:10],
        }

    async def _summarize_findings(self, task_data: dict) -> dict:
        """Summarize research findings."""
        findings = task_data.get("findings", "")
        format_type = task_data.get("format", "brief")

        prompt = f"""Summarize these research findings in a {format_type} format:
{findings[:3000]}

Include:
- Key takeaways
- Important facts
- Source credibility notes"""

        summary = await self.think(prompt)
        return {"summary": summary, "format": format_type}

    async def _summarize_search_results(self, query: str, results: list) -> str:
        """Summarize search results using LLM."""
        if not results:
            return "No results found."

        snippets = "\n".join(f"- {r.get('title','')}: {r.get('snippet','')}" for r in results[:5])
        prompt = f"""Summarize these search results for the query "{query}":\n{snippets}"""
        return await self.think(prompt)

    async def _extract_facts(self, task_data: dict) -> dict:
        """Extract key facts from content."""
        content = task_data.get("content", "")

        prompt = f"""Extract key facts from this content as a JSON array:
{content[:3000]}

Output: {{"facts": [{"fact": "...", "confidence": "high|medium|low", "source": "..."}]}}"""

        result = await self.think(prompt)
        import re
        json_match = re.search(r'\{[\s\S]*"facts"[\s\S]*\}', result)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"facts": [], "error": "Could not extract facts"}

    def get_research_history(self, limit: int = 10) -> list[dict]:
        return self._research_history[-limit:]
