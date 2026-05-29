import importlib
import pkgutil
from pathlib import Path
from typing import List, Dict, Any

from plugins.base import FastCommandPlugin
from Core.logger import get_system_logger

log = get_system_logger("plugin_manager")

class PluginManager:
    def __init__(self):
        self.plugins: List[FastCommandPlugin] = []

    def load_plugins(self):
        """Dynamically load all plugins in the plugins directory."""
        plugins_dir = Path(__file__).resolve().parent
        
        # Iterate through all modules in the plugins directory
        for _, module_name, _ in pkgutil.iter_modules([str(plugins_dir)]):
            if module_name in ["base", "plugin_manager"]:
                continue
                
            try:
                module = importlib.import_module(f"plugins.{module_name}")
                # Find classes that inherit from FastCommandPlugin
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if isinstance(attribute, type) and issubclass(attribute, FastCommandPlugin) and attribute is not FastCommandPlugin:
                        self.plugins.append(attribute())
                        log.debug(f"Loaded plugin: {attribute_name} from {module_name}")
            except Exception as e:
                log.error(f"Failed to load plugin {module_name}: {e}")
                
        log.info(f"Loaded {len(self.plugins)} fast command plugins.")

    def process_command(self, text: str) -> dict | None:
        """Run the text through all plugins."""
        text = text.lower().strip()
        for plugin in self.plugins:
            result = plugin.handle(text)
            if result:
                return result
        return None

# Singleton instance
manager = PluginManager()
manager.load_plugins()

def check_fast_command(text: str) -> dict | None:
    return manager.process_command(text)
