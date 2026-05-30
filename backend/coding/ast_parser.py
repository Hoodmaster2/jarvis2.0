import ast
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ASTParser:
    def parse(self, code: str, language: str = "python") -> dict:
        if language == "python":
            return self._parse_python(code)
        return {"language": language, "error": f"AST parsing not supported for {language}"}

    def _parse_python(self, code: str) -> dict:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "valid": False}
        info = {
            "valid": True,
            "imports": [],
            "functions": [],
            "classes": [],
            "global_vars": [],
            "calls": [],
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info["imports"].append({"name": alias.name, "alias": alias.asname})
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    info["imports"].append({
                        "name": alias.name,
                        "module": node.module,
                        "alias": alias.asname,
                        "level": node.level,
                    })
            elif isinstance(node, ast.FunctionDef):
                info["functions"].append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "docstring": ast.get_docstring(node) or "",
                })
            elif isinstance(node, ast.AsyncFunctionDef):
                info["functions"].append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "async": True,
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append({
                            "name": item.name,
                            "lineno": item.lineno,
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                        })
                info["classes"].append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "bases": [self._get_name(b) for b in node.bases],
                    "methods": methods,
                    "docstring": ast.get_docstring(node) or "",
                })
            elif isinstance(node, ast.Call):
                func_name = self._get_name(node.func)
                if func_name:
                    info["calls"].append({"name": func_name, "lineno": node.lineno})
        return info

    def _get_decorator_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return str(node)

    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice) if hasattr(node, 'slice') else ''}]"
        return ""

    def validate_syntax(self, code: str, language: str = "python") -> dict:
        if language == "python":
            try:
                ast.parse(code)
                return {"valid": True, "errors": []}
            except SyntaxError as e:
                return {"valid": False, "errors": [{"line": e.lineno, "msg": e.msg, "text": e.text}]}
        return {"valid": True, "errors": []}
