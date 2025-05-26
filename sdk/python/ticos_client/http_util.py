import json
import requests
from typing import List, Dict, Any
from datetime import datetime
import logging
from .config import ConfigService

logger = logging.getLogger(__name__)


class HttpUtil:
    """Utility class for making HTTP requests"""

    @staticmethod
    def summarize_conversation(
        conversation_history: List[Dict[str, Any]],
        last_memory: str,
        config_service: ConfigService,
    ) -> str:
        """
        Send a POST request to the summarization API

        Args:
            conversation_history: List of conversation messages
            last_memory: Last memory content
            config_service: ConfigService instance to use for API configuration

        Returns:
            Summary text or None if failed
        """
        try:
            # Get API configuration
            api_key = config_service.get_api_key()
            agent_id = config_service.get_agent_id()
            memory_instructions = config_service.get("model.memory_instructions")

            if not api_key:
                logger.warning("API key is not configured")
                return None
                
            if not agent_id:
                logger.warning("Agent ID is not configured")
                return None

            # Build API URL with agent_id using configured host
            api_host = config_service.get_api_host()
            if "stardust" in api_host:
                # Convert wss:// to https://
                api_base = api_host.replace('wss://', 'https://')
            else:
                # Use default stardust host
                api_base = "https://stardust.ticos.cn"
            
            api_url = f"{api_base}/summarize?agent_id={agent_id}"

            # Prepare conversation history
            history_array = []
            for message in conversation_history:
                msg = {
                    "role": (
                        message.role.value if hasattr(message, "role") else "assistant"
                    ),
                    "content": message.content if hasattr(message, "content") else "",
                }
                history_array.append(msg)

            # Build request parameters
            parameters = {
                "max_length": 4096,
                # "language": "zh-CN"
            }
            
            # Determine if history should be included in conversation
            include_history = True
            if memory_instructions and "{{conversation}}" in memory_instructions:
                include_history = False
                
            parameters["history_in_conversation"] = include_history
            
            # Add latest memory if available
            if last_memory:
                parameters["latest_memory"] = last_memory

            request_body = {
                "conversation_history": history_array,
                "parameters": parameters,
            }

            # Prepare request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            # Log request details
            logger.debug(
                f"Request body: {json.dumps(request_body, indent=2, ensure_ascii=False)}"
            )

            try:
                response = requests.post(
                    api_url,
                    json=request_body,
                    headers=headers,
                    timeout=60,  # Increased timeout to 60 seconds
                )

                if response.status_code == 200:
                    response_data = response.json()

                    summary_array = response_data.get("summary", [])
                    # Join all summary parts with spaces
                    summary = " ".join(summary_array)
                    logger.debug(f"Generated summary: {summary}")
                    return summary
                else:
                    error_msg = (
                        f"Failed to get summary. Status code: {response.status_code}"
                    )
                    try:
                        error_details = response.json()
                        error_msg += f"\nError details: {json.dumps(error_details, indent=2, ensure_ascii=False)}"
                    except:
                        error_msg += f"\nResponse text: {response.text[:500]}"

                    logger.warning(error_msg)
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {str(e)}", exc_info=True)
                return None

        except Exception as e:
            logger.error(f"Error calling summarization API: {e}", exc_info=True)
            return None
