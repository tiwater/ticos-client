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
    def summarize_conversation(conversation_history: List[Dict[str, Any]], last_memory: str, config_service: ConfigService) -> str:
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
            api_url = f"https://stardust.ticos.cn/summarize"
            api_key = config_service.get_api_key()
            
            if not api_key:
                logger.warning("API key is not configured")
                return None
            
            # Get memory instructions from config if available
            memory_instructions = config_service.get("model.memory_instructions", None)
            
            # Prepare request body
            history_array = []
            for message in conversation_history:
                msg = {
                    "role": message.role.value if hasattr(message, 'role') else "assistant",
                    "content": message.content if hasattr(message, 'content') else ""
                }
                history_array.append(msg)
            
            # Build request parameters
            parameters = {
                "max_length": 1024
            }
            
            # Add memory instructions if available
            if memory_instructions:
                # Replace placeholders in memory instructions
                instructions = memory_instructions.replace("{{latest_memory}}", last_memory if last_memory else "")
                # TODO: Now conversation history is handled by another parameter, may change later
                instructions = instructions.replace("{{conversation}}", "")
                parameters["summarize_prompt"] = instructions
            else:
                # Use default prompt
                parameters["summarize_prompt"] = (
                    f"这是之前的记忆：{last_memory if last_memory else ''}，" +
                    "总结上述对话，作为长期记忆供客户端保存。"
                )
            
            request_body = {
                "conversation_history": history_array,
                "parameters": parameters
            }
            
            # Send request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            response = requests.post(
                api_url,
                json=request_body,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                summary_array = response_data.get("summary", [])
                # Join all summary parts with spaces
                summary = " ".join(summary_array)
                return summary
            else:
                logger.warning(f"Failed to get summary. Status code: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling summarization API: {e}", exc_info=True)
            return None
