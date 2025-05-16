import os
import toml
import logging
from pathlib import Path
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class ConfigService:
    """Configuration service for Ticos client."""
    
    def __init__(self, save_mode: str, tf_root_dir: Optional[str] = None):
        """
        Initialize the ConfigService.
        
        Args:
            save_mode: The storage mode (internal or external)
            tf_root_dir: The root directory of the TF card, or None if using internal storage
        """
        self.save_mode = save_mode
        self.user_config_dir = Path.home() / ".config" / "ticos"
        self.tf_config_dir = Path(tf_root_dir) / ".config" / "ticos" if tf_root_dir else None
        self._config = None
        self.initialize()
        
    def initialize(self) -> None:
        """Initialize the configuration service."""
        try:
            # Ensure user config directory exists
            self.user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create default config if it doesn't exist
            user_config_file = self.user_config_dir / "config.toml"
            if not user_config_file.exists():
                default_config = {
                    "agent_id": "",
                    "conversation": {
                        "context_rounds": 6,
                        "memory_rounds": 18
                    }
                }
                with open(user_config_file, "w") as f:
                    toml.dump(default_config, f)
                logger.info(f"Created default user config at: {user_config_file}")
            
            # Load user config
            user_config = toml.load(user_config_file)
            
            # If TF config directory is set, try to merge with TF config
            if self.tf_config_dir:
                self.tf_config_dir.mkdir(parents=True, exist_ok=True)
                tf_config_file = self.tf_config_dir / "config.toml"
                
                # If TF config file exists, load and merge it
                if tf_config_file.exists():
                    tf_config = toml.load(tf_config_file)
                    logger.info(f"Loaded TF config from: {tf_config_file}")
                    self._config = self._merge_configs(user_config, tf_config)
                else:
                    self._config = user_config
            else:
                self._config = user_config
            
        except Exception as e:
            logger.error(f"Failed to initialize config service: {e}")
            raise
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configurations, with the second config taking precedence."""
        merged = base.copy()
        
        for key, value in override.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            path: The path to the configuration value (e.g., "conversation.context_rounds")
            default: The default value to return if the path is not found
            
        Returns:
            The configuration value or default if not found
        """
        try:
            if not self._config:
                return default
                
            parts = path.split(".")
            value = self._config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            
            return value
        except Exception as e:
            logger.warning(f"Error reading config value {path}: {e}")
            return default
    
    def get_agent_id(self) -> str:
        """Get the agent ID."""
        return self.get("agent_id", "")
    
    def get_context_rounds(self) -> int:
        """Get the number of context rounds."""
        return self.get("conversation.context_rounds", 6)
    
    def get_memory_rounds(self) -> int:
        """Get the number of memory rounds."""
        return self.get("conversation.memory_rounds", 18)
    
    def get_api_host(self) -> int:
        """Get the api host."""
        return self.get("api.host", "stardust2.ticos.cn")
    
    def get_api_key(self) -> int:
        """Get the api key for the terminal."""
        return self.get("api.api_key", "")