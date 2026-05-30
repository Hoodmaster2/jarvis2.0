"""
Skill manager - loads, installs, and executes skills from the /skills folder.
"""
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


class Skill:
    """Represents a loaded skill."""

    def __init__(self, name: str, manifest: dict, module):
        self.name = name
        self.manifest = manifest
        self.module = module
        self.enabled = True

    @property
    def description(self) -> str:
        return self.manifest.get("description", "")

    @property
    def permissions(self) -> list:
        return self.manifest.get("permissions", [])

    @property
    def commands(self) -> list:
        return self.manifest.get("commands", [])

    async def execute(self, command: str, **kwargs) -> Any:
        if not self.enabled:
            return {"error": f"Skill '{self.name}' is disabled"}
        if hasattr(self.module, "execute"):
            return await self.module.execute(command, **kwargs)
        return {"error": f"Skill '{self.name}' has no execute function"}


class SkillManager:
    """Manages skill discovery, loading, and execution."""

    def __init__(self, skills_dir: str = None):
        self.skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self._load_all()

    def _load_all(self):
        """Discover and load all skills from the skills directory."""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                self._load_skill(skill_dir)

    def _load_skill(self, skill_dir: Path) -> Optional[Skill]:
        """Load a single skill from its directory."""
        manifest_path = skill_dir / "manifest.json"
        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load manifest for {skill_dir.name}: {e}")
            return None

        name = manifest.get("name", skill_dir.name)

        # Try Python skill first, then JavaScript
        py_file = skill_dir / "skill.py"
        js_file = skill_dir / "skill.js"

        module = None
        if py_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(f"skills.{name}", py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[f"skills.{name}"] = mod
                    spec.loader.exec_module(mod)
                    module = mod
            except Exception as e:
                logger.error(f"Failed to load Python skill '{name}': {e}")

        if module:
            skill = Skill(name, manifest, module)
            self._skills[name] = skill
            logger.info(f"Loaded skill: {name}")
            return skill

        return None

    def reload(self):
        """Reload all skills from disk."""
        self._skills = {}
        self._load_all()

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def get_all_skills(self) -> list[dict]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "enabled": s.enabled,
                "permissions": s.permissions,
                "commands": s.commands,
                "manifest": s.manifest,
            }
            for s in self._skills.values()
        ]

    def enable_skill(self, name: str) -> bool:
        skill = self._skills.get(name)
        if skill:
            skill.enabled = True
            return True
        return False

    def disable_skill(self, name: str) -> bool:
        skill = self._skills.get(name)
        if skill:
            skill.enabled = False
            return True
        return False

    def install_skill(self, source_path: str) -> bool:
        """Install a skill from a directory path."""
        src = Path(source_path)
        if not src.is_dir():
            logger.error(f"Skill source not found: {source_path}")
            return False

        manifest_path = src / "manifest.json"
        if not manifest_path.exists():
            logger.error(f"No manifest.json in {source_path}")
            return False

        name = src.name
        dest = self.skills_dir / name

        import shutil
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

        self._load_skill(dest)
        logger.info(f"Installed skill: {name}")
        return True

    def uninstall_skill(self, name: str) -> bool:
        """Remove a skill."""
        import shutil
        skill_dir = self.skills_dir / name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            self._skills.pop(name, None)
            logger.info(f"Uninstalled skill: {name}")
            return True
        return False

    async def execute_command(self, skill_name: str, command: str, **kwargs) -> Any:
        skill = self._skills.get(skill_name)
        if not skill:
            return {"error": f"Skill '{skill_name}' not found"}
        return await skill.execute(command, **kwargs)
