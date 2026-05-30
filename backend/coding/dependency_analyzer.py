import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    def analyze(self, path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}"}
        result = {
            "python": self._analyze_python_deps(p),
            "node": self._analyze_node_deps(p),
            "files": [],
        }
        return result

    def _analyze_python_deps(self, path: Path) -> dict:
        deps = {"imports": set(), "local_modules": set(), "third_party": set()}
        for f in path.rglob("*.py"):
            if ".git" in f.parts or "__pycache__" in f.parts:
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                for match in re.finditer(r'^(?:from|import)\s+(\S+)', content, re.MULTILINE):
                    module = match.group(1).split(".")[0]
                    if module.startswith("_"):
                        continue
                    deps["imports"].add(module)
            except Exception:
                continue
        stdlib = {"os", "sys", "json", "re", "math", "time", "datetime", "pathlib", "typing",
                  "collections", "functools", "itertools", "asyncio", "logging", "uuid", "enum",
                  "dataclasses", "abc", "copy", "hashlib", "base64", "io", "subprocess", "threading"}
        for imp in deps["imports"]:
            if imp in stdlib:
                continue
            local_path = path / f"{imp}.py"
            local_pkg = path / imp
            if local_path.exists() or (local_pkg.exists() and local_pkg.is_dir()):
                deps["local_modules"].add(imp)
            else:
                deps["third_party"].add(imp)
        return {
            "imports": sorted(deps["imports"]),
            "local_modules": sorted(deps["local_modules"]),
            "third_party": sorted(deps["third_party"]),
        }

    def _analyze_node_deps(self, path: Path) -> dict:
        pkg_file = path / "package.json"
        if not pkg_file.exists():
            return {"has_package_json": False}
        try:
            data = json.loads(pkg_file.read_text(encoding="utf-8"))
            return {
                "has_package_json": True,
                "dependencies": list(data.get("dependencies", {}).keys()),
                "dev_dependencies": list(data.get("devDependencies", {}).keys()),
                "peer_dependencies": list(data.get("peerDependencies", {}).keys()),
            }
        except Exception as e:
            return {"error": str(e)}

    def build_dependency_graph(self, path: str) -> dict:
        analysis = self.analyze(path)
        nodes = []
        edges = []
        added = set()
        for imp in analysis.get("python", {}).get("imports", []):
            if imp not in added:
                nodes.append({"id": imp, "type": "import", "group": "local" if imp in analysis.get("python", {}).get("local_modules", []) else "third_party"})
                added.add(imp)
        for f in Path(path).rglob("*.py"):
            if ".git" in f.parts or "__pycache__" in f.parts:
                continue
            rel = str(f.relative_to(path))
            nodes.append({"id": rel, "type": "file"})
        return {"nodes": nodes, "edges": edges, "analysis": analysis}
