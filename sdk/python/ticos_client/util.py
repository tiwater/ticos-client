import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigUtil:
    """Utility class for configuration management"""
    
    DEFAULT_MEMORY_ROUNDS = 10
    CONFIG_FILE = "ticos_config.json"
    
    @staticmethod
    def get_config_path() -> str:
        """Get the path to the configuration file"""
        config_dir = os.path.join(Path.home(), ".config", "ticos")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, ConfigUtil.CONFIG_FILE)
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get the configuration from the config file"""
        config_path = ConfigUtil.get_config_path()
        if not os.path.exists(config_path):
            # Create default config
            default_config = {
                "memory_rounds": ConfigUtil.DEFAULT_MEMORY_ROUNDS,
                "summarization_api": "",
                "summarization_api_key": ""
            }
            ConfigUtil.save_config(default_config)
            return default_config
            
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return {"memory_rounds": ConfigUtil.DEFAULT_MEMORY_ROUNDS}
    
    @staticmethod
    def save_config(config: Dict[str, Any]) -> bool:
        """Save the configuration to the config file"""
        try:
            with open(ConfigUtil.get_config_path(), 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config file: {e}")
            return False
    
    @staticmethod
    def get_memory_rounds() -> int:
        """Get the number of messages after which to generate a memory"""
        config = ConfigUtil.get_config()
        return config.get("memory_rounds", ConfigUtil.DEFAULT_MEMORY_ROUNDS)
    
    @staticmethod
    def set_memory_rounds(rounds: int) -> bool:
        """Set the number of messages after which to generate a memory"""
        if rounds < 1:
            logger.error("Memory rounds must be at least 1")
            return False
            
        config = ConfigUtil.get_config()
        config["memory_rounds"] = rounds
        return ConfigUtil.save_config(config)
    
    @staticmethod
    def get_summarization_api() -> Optional[str]:
        """Get the URL of the summarization API"""
        config = ConfigUtil.get_config()
        return config.get("summarization_api")
    
    @staticmethod
    def get_summarization_api_key() -> Optional[str]:
        """Get the API key for the summarization API"""
        config = ConfigUtil.get_config()
        return config.get("summarization_api_key")
