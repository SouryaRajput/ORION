"""
Centralized Configuration Loader
Loads config.yaml into a dictionary and provides access via dot notation.
"""

import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

class ConfigDict(dict):
    """A dictionary that supports dot notation access for nested keys."""
    def __getattr__(self, key):
        if key in self:
            val = self[key]
            if isinstance(val, dict):
                return ConfigDict(val)
            return val
        raise AttributeError(f"No such config key: {key}")

def load_config():
    if not CONFIG_PATH.exists():
        return ConfigDict()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ConfigDict(data or {})

config = load_config()
