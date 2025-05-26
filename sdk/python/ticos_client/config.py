import os
import toml
import json
import logging
import requests
from pathlib import Path
from typing import Optional, Any, Dict, Union
from .enums import SaveMode

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
        self.tf_root_dir = tf_root_dir
        self.tf_config_dir = (
            Path(tf_root_dir) / ".config" / "ticos"
            if tf_root_dir
            else Path.home() / ".config" / "ticos"
        )
        self.user_config_dir = Path.home() / ".config" / "ticos"
        self._config = None
        self._session_config = None
        self._server_config = None
        self.initialize()

    def initialize(self) -> None:
        """Initialize the configuration service."""
        try:
            # Ensure user config directory exists
            self.user_config_dir.mkdir(parents=True, exist_ok=True)

            # Check if config.toml exists
            user_config_file = self.user_config_dir / "config.toml"
            if not user_config_file.exists():
                error_msg = f"Configuration file not found: {user_config_file}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # Load config.toml
            self._config = toml.load(user_config_file)

            # Load or create session_config
            self._load_session_config()

            # Fetch server config if agent_id is available
            self._fetch_server_config()

        except Exception as e:
            logger.error(f"Failed to initialize config service: {e}")
            raise

    def _load_session_config(self) -> None:
        """Load the session configuration file."""
        try:
            # Default session config
            default_session_config = {}

            # User session config path
            user_session_file = self.user_config_dir / "session_config"

            # Create default user session config if it doesn't exist
            if not user_session_file.exists():
                with open(user_session_file, "w") as f:
                    json.dump(default_session_config, f, indent=2)
                logger.info(
                    f"Created default user session config at: {user_session_file}"
                )

            # Load user session config
            with open(user_session_file, "r") as f:
                self._session_config = json.load(f)

            # If in EXTERNAL mode, check for TF card session config
            if self.save_mode == SaveMode.EXTERNAL and self.tf_config_dir:
                self.tf_config_dir.mkdir(parents=True, exist_ok=True)
                tf_session_file = self.tf_config_dir / "session_config"

                # If TF session file exists, load and override user session config
                if tf_session_file.exists():
                    with open(tf_session_file, "r") as f:
                        tf_session_config = json.load(f)
                    logger.info(f"Loaded TF session config from: {tf_session_file}")
                    self._session_config = tf_session_config

                    # Write session config to user session file for ticos-agent later use
                    with open(user_session_file, "w") as f:
                        json.dump(self._session_config, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to load session config: {e}")
            raise

    def _fetch_server_config(self) -> None:
        """Fetch configuration from server based on agent_id."""
        try:
            agent_id = self.get_agent_id()
            if not agent_id:
                logger.warning("No agent_id configured, skipping server config fetch")
                return

            api_key = self.get_api_key()
            if not api_key:
                logger.warning("No API key configured, skipping server config fetch")
                return

            url = f"https://api.ticos.ai/v1/agents/{agent_id}"
            headers = {"Authorization": f"Bearer {api_key}"}

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                server_data = response.json()
                if "config" in server_data:
                    self._server_config = server_data["config"]
                    logger.info(
                        f"Successfully fetched server config for agent_id: {agent_id}"
                    )

                    # Merge server config with session config (local has higher priority)
                    self._merge_session_with_server_config()
                else:
                    logger.warning("Server response does not contain config")
            else:
                logger.warning(
                    f"Failed to fetch server config. Status code: {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Error fetching server config: {e}")

    def _merge_session_with_server_config(self) -> None:
        """Merge server config with session config, with session config taking precedence."""
        if not self._server_config or not self._session_config:
            return

        # Create a copy of server config
        merged = {}

        # First, copy all sections from server config
        for section in self._server_config:
            if isinstance(self._server_config[section], dict):
                merged[section] = self._server_config[section].copy()
            else:
                merged[section] = self._server_config[section]

        # Then, override with session config
        for section in self._session_config:
            if (
                section in merged
                and isinstance(self._session_config[section], dict)
                and isinstance(merged[section], dict)
            ):
                # Recursively merge this section
                merged[section] = self._merge_configs(
                    merged[section], self._session_config[section]
                )
            else:
                # Direct override
                merged[section] = self._session_config[section]

        # Update session config with merged result
        self._session_config = merged
        logger.debug(
            f"Merged _session_config: {json.dumps(self._session_config, indent=2, ensure_ascii=False)}"
        )

    def _merge_configs(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two configurations, with the second config taking precedence."""
        merged = base.copy()

        for key, value in override.items():
            if (
                isinstance(value, dict)
                and key in merged
                and isinstance(merged[key], dict)
            ):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            path: The path to the configuration value (e.g., "model.history_conversation_length")
            default: The default value to return if the path is not found

        Returns:
            The configuration value or default if not found
        """
        try:
            # First check if this is a session config path
            if (
                path.startswith("model.")
                or path.startswith("speech.")
                or path.startswith("hearing.")
                or path == "agent_id"
            ):
                if not self._session_config:
                    return default

                parts = path.split(".")
                value = self._session_config
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return default

                return value
            else:
                # Otherwise check main config
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
        return self.get("model.history_conversation_length", 12)

    def get_memory_rounds(self) -> int:
        """Get the number of memory rounds.

        Note: This is now deprecated and redirects to history_conversation_length.
        """
        return self.get_context_rounds()

    def get_api_host(self) -> str:
        """Get the api host."""
        return self.get("api.base_url", "wss://stardust.ticos.cn")

    def get_api_key(self) -> str:
        """Get the api key for the terminal."""
        return self.get("api.api_key", "")
