import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime
import os
from typing import Callable, Dict, Any, Optional, List, Union
from .server import UnifiedServer
from .storage import StorageService, SQLiteStorageService
from .models import Message, MessageRole, Memory, MemoryType
from .enums import SaveMode
from .config import ConfigService
from .utils import find_tf_root_directory

logger = logging.getLogger(__name__)

from .ticos_client_interface import MessageCallbackInterface

class TicosClient(MessageCallbackInterface):
    """
    TicosClient is a Python client for the Ticos Agent system.
    It provides a unified interface for handling both HTTP and WebSocket connections,
    along with message and memory storage capabilities.
    """
    
    def __init__(self, port: int = 9999, save_mode: SaveMode = SaveMode.INTERNAL, tf_root_dir: Optional[str] = None):
        """
        Initialize the TicosClient.
        
        Args:
            port: The port number to run the server on (default: 9999)
            save_mode: The storage mode (internal or external) (default: internal)
            tf_root_dir: The root directory of the TF card, or None if using internal storage (default: None)
        """
        self.port = port
        self.save_mode = save_mode
        self.tf_root_dir = tf_root_dir
        self.server: Optional[UnifiedServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        self.storage: Optional[StorageService] = None
        self.message_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.motion_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.emotion_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.message_counter = 0  # Add message counter
        
        # Initialize config service
        self.config_service = ConfigService(save_mode, tf_root_dir)
        self.memory_rounds = self.config_service.get_memory_rounds()
        self.date_format = "%Y-%m-%d %H:%M:%S"

    def enable_local_storage(self, storage_service: Optional[StorageService] = None):
        """
        Enable local storage with the provided storage service.
        If no storage service is provided, a default SQLiteStorageService will be used.
        
        Args:
            storage_service: Optional custom storage service implementation
        """
        if storage_service is None:
            storage_service = SQLiteStorageService()
        
        # Set storage directory based on save mode
        if self.save_mode == SaveMode.EXTERNAL and self.tf_root_dir:
            storage_service.set_store_root_dir(self.tf_root_dir)
        else:
            # For internal storage, use a default directory
            storage_service.set_store_root_dir(os.path.join(os.getcwd(), 'storage'))
        
        try:
            storage_service.initialize()
            self.storage = storage_service
            logger.info(f"Local storage enabled: {storage_service.__class__.__name__}")
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            raise

    def set_message_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Set the message handler function.
        
        Args:
            handler: Function that takes a message dictionary as argument
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self.server.message_handler = handler
        logger.debug("Message handler set")

    def set_motion_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Set the motion handler.
        
        Args:
            handler: A callable that takes a dictionary of parameters
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self.motion_handler = handler
    
    def set_emotion_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Set the emotion handler.
        
        Args:
            handler: A callable that takes a dictionary of parameters
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self.emotion_handler = handler
        logger.debug("Emotion handler set")

    def start(self):
        """
        Start the Ticos server.
        """
        if self.running:
            logger.warning("Ticos server is already running")
            return
        
        # Start the server in a separate thread
        def run_server():
            try:
                self.server = UnifiedServer(
                    message_callback=self,
                    port=self.port,
                    storage_service=self.storage,
                )
                import uvicorn
                uvicorn.run(self.server.app, host="0.0.0.0", port=self.port, log_level="info")
            except Exception as e:
                logger.error(f"Failed to start server: {e}")
                self.running = False
                return False
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        logger.info(f"Ticos server started on port {self.port}")

    def stop(self):
        """Stop the server and clean up resources."""
        if not self.running:
            return
            
        logger.info("Stopping Ticos server...")
        self.running = False
        
        try:
            # Signal the server to shut down gracefully
            if hasattr(self, 'server') and self.server:
                # Create a new event loop for the shutdown process
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Run the shutdown coroutine
                    loop.run_until_complete(self.server.shutdown())
                except Exception as e:
                    logger.error(f"Error during server shutdown: {e}")
                finally:
                    loop.close()
            
            # Wait for the server thread to finish
            if hasattr(self, 'server_thread') and self.server_thread.is_alive():
                self.server_thread.join(timeout=2.0)
                if self.server_thread.is_alive():
                    logger.warning("Server thread did not shut down gracefully")
            
            logger.info("Ticos server stopped")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
        finally:
            # Ensure we clean up resources even if there's an error
            self.running = False
    
    def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to all connected WebSocket clients.
        
        Args:
            message: Dictionary containing the message data
            
        Returns:
            bool: True if the message was sent successfully
        """
        try:
            if not isinstance(message, dict):
                logger.error("Message must be a dictionary")
                return False
                
            if "name" not in message:
                logger.error("Message must contain a 'name' field")
                return False
                
            if "timestamp" not in message["arguments"]:
                message["arguments"]["timestamp"] = datetime.utcnow().isoformat()
            
            logger.debug(f"Sending message: {message}")
            
            # Broadcast the message
            if self.server and hasattr(self.server, 'broadcast_message'):
                try:
                    if hasattr(self.server, 'loop') and self.server.loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            self.server.broadcast_message(message),
                            self.server.loop
                        )
                        future.result(timeout=5.0)
                    else:
                        logger.warning("Server event loop is not running")
                except Exception as e:
                    logger.warning(f"Error broadcasting message: {e}")
            else:
                logger.debug("Server not available for broadcasting")
            
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            return False
            
    def is_running(self):
        """Check if the server is running"""
        return self.running and bool(self.server)


    
    def handle_message(self, message: Dict[str, Any]) -> bool:
        """
        Handle an incoming message.
        
        Args:
            message: The message to handle
            
        Returns:
            bool: True if the message was handled successfully
        """
        try:
            # Save the message to local storage if enabled
            if self.storage:
                try:
                    # Create a copy of the message for storage
                    storage_message = message.copy()
                    
                    # Convert message to Message model
                    role = MessageRole.USER if message.get('name') == 'test_message' else MessageRole.ASSISTANT
                    
                    # Check if this is a response to a previous message
                    if 'in_response_to' in message.get('arguments', {}):
                        role = MessageRole.ASSISTANT
                    
                    # Ensure storage message has an ID
                    if 'id' not in storage_message:
                        storage_message['id'] = str(uuid.uuid4())
                    
                    # Store the original message content
                    msg = Message(
                        id=storage_message['id'],
                        role=role,
                        content=json.dumps(message),  # Store the original message
                        datetime=datetime.now().strftime(self.date_format)
                    )
                    self.storage.save_message(msg)
                    logger.debug("Message saved to storage")
                    
                    # Check if we need to generate a memory
                    self.message_counter += 1
                    if self.message_counter >= self.memory_rounds:
                        self.generate_memory()
                        self.message_counter = 0
                        
                except Exception as e:
                    logger.error(f"Failed to save message to storage: {e}")
                    return False
                    
            # Call the generic message handler first
            if self.message_handler:
                self.message_handler(message)
                logger.debug("Called generic message handler")
            
            # Call the appropriate handler based on message type
            message_name = message.get('name')
            arguments = message.get('arguments', {})
            
            try:
                # Log the received message for debugging
                logger.debug(f"Handling message: {message_name} with args: {arguments}")
                
                # Call the appropriate handler
                if message_name == "motion":
                    if self.motion_handler:
                        self.motion_handler(arguments)
                        logger.debug("Called motion handler")
                    else:
                        logger.warning("No motion handler registered")
                elif message_name == "emotion":
                    if self.emotion_handler:
                        self.emotion_handler(arguments)
                        logger.debug("Called emotion handler")
                    else:
                        logger.warning("No emotion handler registered")
                elif message_name == "motion_and_emotion":
                    if self.motion_handler:
                        self.motion_handler(arguments)
                        logger.debug("Called motion handler (from motion_and_emotion)")
                    if self.emotion_handler:
                        self.emotion_handler(arguments)
                        logger.debug("Called emotion handler (from motion_and_emotion)")
                else:
                    logger.info(f"Received unhandled message: {message}")
                    
                return True
                
            except Exception as e:
                logger.error(f"Error handling message {message_name}: {e}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return False

    def generate_memory(self) -> None:
        """
        Generate a memory from recent conversation history.
        This is called after a certain number of messages have been processed.
        """
        if not self.storage:
            return
            
        try:
            # Get the latest messages
            messages = self.storage.get_messages(0, self.memory_rounds, True)
            
            # Get the latest memory for context
            latest_memory = self.storage.get_latest_memory()
            last_memory_content = latest_memory["content"] if latest_memory else ""
            
            # Use a summarization API or generate a simple summary
            # In Java version, this calls HttpUtil.summarizeConversation
            memory_content = self._summarize_conversation(messages, last_memory_content)
            
            if memory_content:
                # Save the new memory
                memory = Memory(
                    type=MemoryType.LONG_TERM,
                    content=memory_content,
                    datetime=datetime.now().strftime(self.date_format)
                )
                self.storage.save_memory(memory)
                logger.info(f"Generated new memory: {memory_content}")
        except Exception as e:
            logger.error(f"Error generating memory: {e}", exc_info=True)
    
    def _summarize_conversation(self, messages: List[Dict[str, Any]], last_memory: str) -> str:
        """
        Summarize a conversation to generate a memory.
        
        Args:
            messages: List of recent messages
            last_memory: The content of the most recent memory, if any
            
        Returns:
            str: A summary of the conversation
        """
        try:
            # This is a simplified implementation
            # In a real implementation, you might want to call an external API
            # or use a more sophisticated summarization algorithm
            
            # Extract message contents
            contents = []
            for msg in messages:
                try:
                    content = json.loads(msg["content"]) if isinstance(msg["content"], str) else msg["content"]
                    if isinstance(content, dict) and "arguments" in content:
                        if "content" in content["arguments"]:
                            contents.append(f"{msg['role']}: {content['arguments']['content']}")
                        elif "text" in content["arguments"]:
                            contents.append(f"{msg['role']}: {content['arguments']['text']}")
                except Exception as e:
                    logger.warning(f"Error processing message for summarization: {e}")
            
            if not contents:
                return ""
                
            # Simple summarization: combine the messages
            summary = "Recent conversation: " + "; ".join(contents[-3:])  # Just take the last 3 messages
            
            # Add context from the last memory if available
            if last_memory:
                summary = f"Previous context: {last_memory}. {summary}"
                
            return summary[:500]  # Limit length
            
        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}")
            return ""


class DefaultMessageHandler:
    """
    Default implementation of message handler.
    This can be used as a base class for custom message handlers.
    """
    def handle_message(self, message: Dict[str, Any]):
        """
        Handle an incoming message.
        
        Args:
            message: The message dictionary
        """
        print(f"[DefaultMessageHandler] Received message: {json.dumps(message, indent=2)}")
