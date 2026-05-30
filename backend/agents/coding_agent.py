import json
import logging
import os
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from coding.repo_indexer import RepoIndexer
from coding.semantic_search import SemanticSearch
from coding.git_manager import GitManager
from coding.patch_engine import PatchEngine
from coding.dependency_analyzer import DependencyAnalyzer
from coding.workspace_manager import WorkspaceManager
from coding.code_memory import CodeMemory
from coding.ast_parser import ASTParser

logger = logging.getLogger(__name__)

CODING_SYSTEM_PROMPT = """You are JARVIS Coding Agent with full repository intelligence.
You can index repos, search code semantically, analyze dependencies, manage git, generate patches, and debug errors.
Always analyze before modifying. Validate patches before applying. Use git for safety."""


class CodingAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = CODING_SYSTEM_PROMPT
        self.indexer = RepoIndexer()
        self.semantic_search = SemanticSearch()
        self.git = GitManager()
        self.patch_engine = PatchEngine()
        self.dep_analyzer = DependencyAnalyzer()
        self.workspace_manager = WorkspaceManager()
        self.code_memory = CodeMemory()
        self.ast_parser = ASTParser()
        self._history = []

    async def execute_task(self, task_data: dict) -> Any:
        action = task_data.get("action", "analyze_or_implement")
        handlers = {
            "analyze_or_implement": self._analyze_or_implement,
            "analyze": self._analyze_project,
            "index_project": self._index_project,
            "search_code": self._search_code,
            "generate_patch": self._generate_patch,
            "apply_patch": self._apply_patch,
            "debug": self._debug_error,
            "git_status": self._git_status,
            "git_log": self._git_log,
            "git_diff": self._git_diff,
            "git_commit": self._git_commit,
            "analyze_deps": self._analyze_deps,
            "validate_syntax": self._validate_syntax,
            "explain_code": self._explain_code,
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(task_data)

    async def _analyze_or_implement(self, task_data: dict) -> dict:
        request = task_data.get("request", "")
        project_path = task_data.get("project_path", "")
        prompt = f"""Analyze this coding request:
Request: {request}
Project path: {project_path}
Determine: 1) Code analysis needed? 2) New file? 3) Modification? 4) Bug fix? 5) Tests?
Output JSON: {{"primary_action": "analyze|implement|debug|test|index", "files_to_examine": [...], "estimated_effort": "small|medium|large"}}"""
        plan = await self.think(prompt)
        import re
        json_match = re.search(r'\{[\s\S]*"primary_action"[\s\S]*\}', plan)
        if json_match:
            try:
                decision = json.loads(json_match.group())
                action = decision.get("primary_action", "analyze")
                if action == "debug":
                    return await self._debug_error({"request": request, "path": project_path})
                elif action in ("implement", "test"):
                    return await self._generate_patch({"request": request, "project_path": project_path})
                elif action == "index":
                    return await self._index_project({"path": project_path})
                else:
                    return await self._analyze_project({"path": project_path, "request": request})
            except json.JSONDecodeError:
                pass
        return await self._analyze_project({"path": project_path, "request": request})

    async def _analyze_project(self, task_data: dict) -> dict:
        path = task_data.get("path", "")
        request = task_data.get("request", "")
        index = self.indexer.index_project(path)
        summary = self.code_memory.get_repo_summary(path)
        analysis = await self.think(
            f"Analyze this project for request: {request}\nIndex: {json.dumps(index, indent=2)[:3000]}"
        )
        self.code_memory.store_repo_summary(path, analysis, list(index.get("languages", {}).keys()))
        self._history.append({"action": "analyze", "project": path})
        return {"project_index": index, "analysis": analysis}

    async def _index_project(self, task_data: dict) -> dict:
        path = task_data.get("path", "")
        index = self.indexer.index_project(path)
        if "error" in index:
            return index
        docs = []
        for f in index.get("files", []):
            content = self.indexer.get_file_content(path, f["path"])
            if content:
                docs.append({"path": f["path"], "content": content[:2000]})
        self.semantic_search.index_documents(docs)
        self.code_memory.store_repo_summary(path, f"Indexed {index['file_count']} files", list(index.get("languages", {}).keys()))
        self._history.append({"action": "index", "project": path})
        return {"status": "indexed", "files": index["file_count"], "languages": index["languages"]}

    async def _search_code(self, task_data: dict) -> dict:
        query = task_data.get("query", "")
        path = task_data.get("path", "")
        results = self.semantic_search.search(query, k=10)
        if not results:
            results = [{"path": f["path"], "score": 0} for f in self.indexer.get_index(path).get("files", [])[:10]]
        return {"query": query, "results": results}

    async def _generate_patch(self, task_data: dict) -> dict:
        request = task_data.get("request", "")
        project_path = task_data.get("project_path", "")
        prompt = f"""Generate code changes for: {request}
Project: {project_path}
Output JSON: {{"files": [{{"path": "relative/path", "action": "create|modify|delete", "content": "file content", "description": "what this does"}}]}}"""
        result = await self.think(prompt)
        import re
        json_match = re.search(r'\{[\s\S]*"files"[\s\S]*\}', result)
        patches = []
        if json_match:
            try:
                patch_plan = json.loads(json_match.group())
                for fchange in patch_plan.get("files", []):
                    file_path = str(Path(project_path) / fchange["path"])
                    old_content = ""
                    if Path(file_path).exists():
                        old_content = Path(file_path).read_text(encoding="utf-8")
                    patch = self.patch_engine.create_patch(
                        file_path, old_content, fchange.get("content", ""),
                        description=fchange.get("description", ""),
                    )
                    patches.append(patch.to_dict())
            except json.JSONDecodeError:
                pass
        self._history.append({"action": "generate_patch", "files": len(patches)})
        return {"patches": patches, "status": "pending_approval" if patches else "no_changes"}

    async def _apply_patch(self, task_data: dict) -> dict:
        patch_id = task_data.get("patch_id", "")
        approved = task_data.get("approved", False)
        if approved:
            self.patch_engine.approve_patch(patch_id)
            return self.patch_engine.apply_patch(patch_id)
        return {"status": "not_approved", "patch_id": patch_id}

    async def _debug_error(self, task_data: dict) -> dict:
        request = task_data.get("request", "")
        error_text = task_data.get("error", task_data.get("request", ""))
        path = task_data.get("path", "")
        prompt = f"""Debug this error:
Error: {error_text}
Project: {path}
Output JSON: {{"root_cause": "...", "fix_suggestion": "...", "confidence": "high|medium|low", "files_to_modify": [...], "test_command": "..."}}"""
        analysis = await self.think(prompt)
        import re
        json_match = re.search(r'\{[\s\S]*"root_cause"[\s\S]*\}', analysis)
        debug_info = {}
        if json_match:
            try:
                debug_info = json.loads(json_match.group())
            except json.JSONDecodeError:
                debug_info = {"analysis": analysis[:500]}
        self.code_memory.store_fix(path or "unknown", error_text, analysis)
        self._history.append({"action": "debug", "error": error_text[:100]})
        return {"debug_info": debug_info, "raw_analysis": analysis[:500]}

    async def _git_status(self, task_data: dict) -> dict:
        path = task_data.get("path", "")
        return self.git.get_status(path)

    async def _git_log(self, task_data: dict) -> dict:
        path = task_data.get("path", "")
        return {"commits": self.git.get_log(path)}

    async def _git_diff(self, task_data: dict) -> dict:
        path = task_data.get("path", "")
        return {"diff": self.git.get_diff(path)}

    async def _git_commit(self, task_data: dict) -> dict:
        path = task_data.get("path", "")
        message = task_data.get("message", "JARVIS auto-commit")
        return self.git.create_commit(path, message)

    async def _analyze_deps(self, task_data: dict) -> dict:
        path = task_data.get("path", "")
        return self.dep_analyzer.analyze(path)

    async def _validate_syntax(self, task_data: dict) -> dict:
        code = task_data.get("code", "")
        language = task_data.get("language", "python")
        return self.ast_parser.validate_syntax(code, language)

    async def _explain_code(self, task_data: dict) -> dict:
        code = task_data.get("code", "")
        context = task_data.get("context", "")
        ast_info = self.ast_parser.parse(code)
        prompt = f"Explain this code:\nContext: {context}\nAST: {json.dumps(ast_info, indent=2)[:1000]}\nCode:\n```\n{code[:3000]}\n```"
        explanation = await self.think(prompt)
        return {"explanation": explanation, "ast": ast_info}

    def get_history(self, limit: int = 20) -> list:
        return self._history[-limit:]
