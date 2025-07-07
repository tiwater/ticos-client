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
    def update_variables(config_service, priority="medium"):
        """
        Update or delete variables for the device by sending them to the server.
        
        This method sends the variables from session_config to the server via HTTP POST request.
        Variables with null values will be deleted, others will be updated or added.
        
        Args:
            config_service: ConfigService instance to use for API configuration
            priority: Priority level for the update operation ('low', 'medium', 'high')
                      Default is 'medium'
        
        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:            
            variables = config_service.get('variables', {})
            if not variables:
                logger.warning("Variables section is empty in session_config")
                return False
            
            # Get API key for authentication
            api_key = config_service.get_api_key()
            if not api_key:
                logger.error("API key is not configured")
                return False
            
            # Get API host and convert WebSocket URL to HTTP URL if needed
            api_host = config_service.get_api_host()
            if api_host.startswith('wss://'):
                api_base = api_host.replace('wss://', 'https://')
            elif api_host.startswith('ws://'):
                api_base = api_host.replace('ws://', 'http://')
            else:
                api_base = f"https://{api_host}"
            
            # Build API URL
            api_url = f"{api_base}/variables"
            if priority:
                api_url += f"?priority={priority}"
            
            # Prepare headers with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Send POST request to update variables
            response = requests.post(
                api_url,
                json=variables,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully updated variables with priority '{priority}'")
                return True
            else:
                logger.error(f"Failed to update variables. Status code: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating variables: {e}", exc_info=True)
            return False

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

            # Get max_length from config, default to 2048 if not set
            max_response_output_tokens = config_service.get("model.max_response_output_tokens", 4096)
            max_length = max_response_output_tokens // 2
            
            # Build request parameters
            parameters = {
                "max_length": max_length,
                # "language": "zh-CN"
            }
            
            # Set default memory instructions if empty or None
            if not memory_instructions:
                memory_instructions = "You are an AI companion. Please generate long-term memory based on previous memory \n```\n{{latest_memory}}\n```\n and latest conversations:\n```\n {{conversation}} \n```\nwith the user to facilitate better communication in the future."
            
            # Determine if history should be included in conversation
            include_history = True
            if "{{conversation}}" in memory_instructions:
                include_history = False
            
            # Add memory_instructions as summarize_prompt
            parameters["summarize_prompt"] = memory_instructions
                
            parameters["history_in_conversation"] = include_history
            
            # Add latest memory if available
            if last_memory:
                # Add instruction to focus on key information and limit length
                if isinstance(last_memory, str):
                    last_memory = f"{last_memory}\n\nPlease ensure to summarize the key information and make sure that the newly generated long-term memory does not exceed {max_length} characters in length."
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
                    timeout=180,  # Increased timeout to 60 seconds
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
