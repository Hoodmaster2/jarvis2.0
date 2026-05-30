import difflib
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class Patch:
    def __init__(self, file_path: str, old_content: str, new_content: str, description: str = ""):
        self.id = str(uuid4())
        self.file_path = file_path
        self.old_content = old_content
        self.new_content = new_content
        self.description = description
        self.created_at = time.time()
        self.applied = False
        self.approved = False

    def get_diff(self) -> str:
        old_lines = self.old_content.splitlines(keepends=True)
        new_lines = self.new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile=self.file_path, tofile=self.file_path, n=3)
        return "".join(diff)

    def apply(self) -> bool:
        try:
            Path(self.file_path).write_text(self.new_content, encoding="utf-8")
            self.applied = True
            return True
        except Exception as e:
            logger.error(f"Failed to apply patch {self.id}: {e}")
            return False

    def revert(self) -> bool:
        try:
            Path(self.file_path).write_text(self.old_content, encoding="utf-8")
            self.applied = False
            return True
        except Exception as e:
            logger.error(f"Failed to revert patch {self.id}: {e}")
            return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "diff": self.get_diff(),
            "description": self.description,
            "applied": self.applied,
            "approved": self.approved,
            "created_at": self.created_at,
        }


class PatchEngine:
    def __init__(self):
        self._patches: Dict[str, Patch] = {}
        self._history: List[Patch] = []

    def create_patch(self, file_path: str, old_content: str, new_content: str, description: str = "") -> Patch:
        patch = Patch(file_path, old_content, new_content, description)
        self._patches[patch.id] = patch
        return patch

    def create_patch_from_diff(self, file_path: str, diff_text: str) -> Optional[Patch]:
        try:
            old_content = Path(file_path).read_text(encoding="utf-8")
            new_content = self._apply_unified_diff(old_content, diff_text)
            if new_content:
                return self.create_patch(file_path, old_content, new_content, "From diff")
        except Exception as e:
            logger.error(f"Failed to create patch from diff: {e}")
        return None

    def _apply_unified_diff(self, original: str, diff: str) -> Optional[str]:
        try:
            result = difflib.patch(original.splitlines(keepends=True), diff)
            return "".join(result) if result else None
        except Exception:
            patches = list(difflib.patch(original, diff))
            return "".join(patches) if patches else None

    def approve_patch(self, patch_id: str) -> bool:
        patch = self._patches.get(patch_id)
        if patch:
            patch.approved = True
            return True
        return False

    def apply_patch(self, patch_id: str) -> dict:
        patch = self._patches.get(patch_id)
        if not patch:
            return {"error": "Patch not found"}
        if not patch.approved:
            return {"error": "Patch not approved"}
        ok = patch.apply()
        if ok:
            self._history.append(patch)
            del self._patches[patch_id]
        return {"status": "applied" if ok else "failed", "patch_id": patch_id}

    def revert_patch(self, patch_id: str) -> dict:
        patch = next((p for p in self._history if p.id == patch_id), None)
        if not patch:
            return {"error": "Applied patch not found"}
        ok = patch.revert()
        return {"status": "reverted" if ok else "failed"}

    def get_pending_patches(self) -> list:
        return [p.to_dict() for p in self._patches.values()]

    def get_applied_patches(self, limit: int = 20) -> list:
        return [p.to_dict() for p in self._history[-limit:]]

    def get_patch(self, patch_id: str) -> Optional[dict]:
        patch = self._patches.get(patch_id) or next((p for p in self._history if p.id == patch_id), None)
        return patch.to_dict() if patch else None
