"""
Configuration manager for JARVIS.
Loads from config/default.json and overrides with .env values.
"""
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.json"


class Config:
    """Central configuration for JARVIS."""

    def __init__(self, config_path=None):
        self._data = self._load_defaults(config_path)
        self._apply_env_overrides()

    def _load_defaults(self, config_path=None):
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if path and path.exists():
            with open(path) as f:
                return json.load(f)
        logger.warning(f"Config file not found at {path}, using fallback defaults")
        return {}

    def _apply_env_overrides(self):
        env_map = {
            "OLLAMA_HOST": ("ollama", "host"),
            "OLLAMA_MODEL": ("ollama", "model"),
            "MEMORY_ENABLED": ("memory", "enabled"),
            "MEMORY_PATH": ("memory", "path"),
            "STT_ENGINE": ("voice", "stt_engine"),
            "TTS_ENGINE": ("voice", "tts_engine"),
            "JARVIS_API_PORT": ("network", "api_port"),
            "JARVIS_API_HOST": ("network", "api_host"),
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FILE": ("logging", "file"),
        }
        for env_key, (section, key) in env_map.items():
            val = os.getenv(env_key)
            if val is not None:
                self._ensure_section(section)
                if key in ("enabled",) and val.lower() in ("true", "1", "yes"):
                    self._data[section][key] = True
                elif key in ("enabled",) and val.lower() in ("false", "0", "no"):
                    self._data[section][key] = False
                elif key in ("api_port", "context_size", "num_predict", "timeout", "max_entries"):
                    self._data[section][key] = int(val)
                else:
                    self._data[section][key] = val

    def _ensure_section(self, section):
        if section not in self._data:
            self._data[section] = {}

    def get(self, *keys, default=None):
        val = self._data
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return default
        return val if val is not None else default

    def set(self, *keys, value):
        if len(keys) < 2:
            raise ValueError("Need at least section and key")
        self._ensure_section(keys[0])
        val = self._data
        for key in keys[:-1]:
            if key not in val:
                val[key] = {}
            val = val[key]
        val[keys[-1]] = value
        self._save()

    def _save(self):
        path = Path(__file__).parent.parent / "config" / "default.json"
        with open(path, "w") as f:
            json.dump(self._data, f, indent=2)

    def to_dict(self):
        return self._data

    @property
    def ollama_model(self):
        return self.get("ollama", "model", default="qwen3")

    @property
    def ollama_host(self):
        return self.get("ollama", "host", default="http://localhost:11434")

    @property
    def memory_enabled(self):
        return self.get("memory", "enabled", default=True)

    @property
    def memory_path(self):
        return self.get("memory", "path", default="./data/memory.db")
