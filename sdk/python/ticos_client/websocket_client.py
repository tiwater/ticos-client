import json
import logging
import uuid
import websocket
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class TicosWebSocketClient:
    """
    WebSocket client for Ticos API communication.
    Handles realtime connections to the Ticos API for memory updates and other operations.
    """

    def __init__(self, config_service):
        """
        Initialize the WebSocket client.
        
        Args:
            config_service: The configuration service to get API host and key
        """
        self.config_service = config_service
        self.ws = None
        self.on_message_callback = None
        self.on_error_callback = None
        self.on_close_callback = None
        self.on_open_callback = None
        
    def _get_websocket_url(self) -> str:
        """
        Get the WebSocket URL for realtime API.
        
        Returns:
            str: The WebSocket URL
        """
        api_host = self.config_service.get_api_host()
        # Ensure the URL starts with wss:// or ws://
        if not api_host.startswith(('wss://', 'ws://')):
            api_host = f"wss://{api_host}"
        
        # Add /realtime path
        return f"{api_host}/realtime"
    
    def _get_headers(self) -> list:
        """
        Get the headers for WebSocket connection.
        
        Returns:
            list: List of header strings
        """
        api_key = self.config_service.get_api_key()
        return [
            f"Authorization: Bearer {api_key}",
            "OpenAI-Beta: realtime=v1"
        ]
    
    def _on_message(self, ws, message):
        """
        Handle incoming WebSocket messages.
        
        Args:
            ws: WebSocket connection
            message: The received message
        """
        try:
            data = json.loads(message)
            logger.debug(f"Received WebSocket message: {json.dumps(data, indent=2)}")
            
            if self.on_message_callback:
                self.on_message_callback(data)
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """
        Handle WebSocket errors.
        
        Args:
            ws: WebSocket connection
            error: The error
        """
        logger.error(f"WebSocket error: {error}")
        if self.on_error_callback:
            self.on_error_callback(error)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        Handle WebSocket connection close.
        
        Args:
            ws: WebSocket connection
            close_status_code: Status code for closing
            close_msg: Close message
        """
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        if self.on_close_callback:
            self.on_close_callback(close_status_code, close_msg)
    
    def _on_open(self, ws):
        """
        Handle WebSocket connection open.
        
        Args:
            ws: WebSocket connection
        """
        logger.info("WebSocket connection established")
        if self.on_open_callback:
            self.on_open_callback()
    
    def connect(self):
        """
        Connect to the WebSocket server.
        
        This establishes a persistent WebSocket connection that can be used
        to listen for server events. For sending messages, we use separate
        connections to avoid complexity with threading.
        """
        try:
            url = self._get_websocket_url()
            headers = self._get_headers()
            
            logger.info(f"Connecting to WebSocket server: {url}")
            
            self.ws = websocket.WebSocketApp(
                url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # 启动WebSocket连接（非阻塞）
            # 注意：如果需要保持长连接，应该在单独的线程中调用run_forever()
            # 例如：threading.Thread(target=self.ws.run_forever).start()
        except Exception as e:
            logger.error(f"Error creating WebSocket connection: {e}")
            raise

    def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to the Ticos server via WebSocket.
        
        Args:
            message: Dictionary containing the message data
            
        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        if not isinstance(message, dict):
            logger.error("Message must be a dictionary")
            return False

        try:
            # Get WebSocket URL and headers
            ws_url = self._get_websocket_url()
            headers = self._get_headers()

            # Create a short-lived WebSocket connection
            ws = websocket.create_connection(ws_url, header=headers)
            
            try:
                # Ensure the message has required fields
                if 'event_id' not in message:
                    message['event_id'] = f"evt_{uuid.uuid4().hex[:8]}"
                
                # Send the message
                ws.send(json.dumps(message))
                logger.debug("Message sent successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                return False
                
            finally:
                # Always close the WebSocket connection
                try:
                    ws.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
                    
        except Exception as e:
            logger.error(f"Error establishing WebSocket connection: {e}")
            return False
    
    def send_user_prompt_update(self, agent_id: str, memory_content: str) -> bool:
        """
        Send a session update with memory content.
        
        Args:
            agent_id: The agent ID
            memory_content: The memory content to include
            
        Returns:
            bool: True if the message was sent successfully
        """
        try:
            
            # 使用单独的连接发送消息，避免长连接的复杂性
            url = self._get_websocket_url()
            headers = self._get_headers()
            # 创建连接，发送消息，然后关闭
            ws = websocket.create_connection(url, header=headers)

            # Create message payload
            event_id = f"evt_{uuid.uuid4().hex[:8]}"
            msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            message = {
                "event_id": event_id,
                "type": "conversation.item.create",
                "previous_item_id": "initial_user_prompt",
                "item": {
                    "id": msg_id,
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": memory_content
                        }
                    ]
                }
            }
            
            
            ws.send(json.dumps(message))

            # Create message payload
            event_id = f"evt_{uuid.uuid4().hex[:8]}"
            msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            message = {
                "event_id": event_id,
                "type": "conversation.item.create",
                "previous_item_id": "initial_assistant_prompt",
                "item": {
                    "id": msg_id,
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "OK"
                        }
                    ]
                }
            }
            
            
            ws.send(json.dumps(message))
            logger.debug(f"Sent session update: {json.dumps(message, indent=2)}")
            ws.close()
            
            return True
        except Exception as e:
            logger.error(f"Error sending session update: {e}")
            return False
    
    def start_listening(self):
        """
        Start listening for WebSocket messages in a background thread.
        This is useful if you want to maintain a persistent connection
        to receive server-sent events.
        """
        if not self.ws:
            self.connect()
            
        import threading
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True  # 设置为守护线程，这样主程序退出时线程会自动结束
        self.ws_thread.start()
        logger.info("Started WebSocket listener thread")
        
    def is_connected(self):
        """
        Check if the WebSocket connection is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.ws is not None and hasattr(self.ws, "sock") and self.ws.sock is not None
    
    def close(self):
        """
        Close the WebSocket connection.
        """
        if self.ws:
            self.ws.close()
            self.ws = None
