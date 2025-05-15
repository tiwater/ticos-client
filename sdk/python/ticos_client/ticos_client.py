import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, Dict, Any, Optional, List, Union
from .server import UnifiedServer
from .storage import StorageService, SQLiteStorageService
from .models import Message, MessageRole, Memory, MemoryType
from .util import ConfigUtil

logger = logging.getLogger(__name__)

class TicosClient:
    """
    TicosClient is a Python client for the Ticos Agent system.
    It provides a unified interface for handling both HTTP and WebSocket connections,
    along with message and memory storage capabilities.
    """
    
    def __init__(self, port: int = 9999):
        """
        Initialize the TicosClient.
        
        Args:
            port: The port number to run the server on (default: 9999)
        """
        self.port = port
        self.storage: Optional[StorageService] = None
        self.server: Optional[UnifiedServer] = None
        self.message_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.motion_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.emotion_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.running = False
        self.message_counter = 0
        self.memory_rounds = ConfigUtil.get_memory_rounds()
        self.date_format = "%Y-%m-%d %H:%M:%S"

    def enable_local_storage(self, storage: Optional[StorageService] = None):
        """
        Enable local storage with the provided storage service.
        If no storage service is provided, a default SQLiteStorageService will be used.
        
        Args:
            storage: Optional custom storage service implementation
        """
        if storage is None:
            storage = SQLiteStorageService()
        self.storage = storage
        logger.info(f"Local storage enabled: {storage.__class__.__name__}")

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
        self.server.motion_handler = handler
    
    def set_emotion_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Set the emotion handler.
        
        Args:
            handler: A callable that takes a dictionary of parameters
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self.server.emotion_handler = handler
        logger.debug("Emotion handler set")

    def start(self) -> bool:
        """
        Start the Ticos server.
        
        Returns:
            bool: True if server started successfully, False otherwise
        """
        if self.running:
            logger.warning("Server is already running")
            return True
            
        try:
            self.server = UnifiedServer(
                port=self.port,
                storage_service=self.storage,
                message_handler=self.message_handler,
                motion_handler=self.motion_handler,
                emotion_handler=self.emotion_handler
            )
            
            # Start the server in a separate thread
            self.server_thread = threading.Thread(
                target=self.server.run,
                daemon=True
            )
            self.server_thread.start()
            
            # Give the server some time to start
            time.sleep(0.5)  # Increased from 0.1 to 0.5 seconds
            
            # Check if the server is actually running
            if not hasattr(self.server, 'is_running') or not self.server.is_running():
                logger.error("Server failed to start")
                self.running = False
                return False
                
            self.running = True
            logger.info(f"Ticos server started on port {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.running = False
            return False
    
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
        Send a message to the server.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        try:
            # Validate message format
            if not isinstance(message, dict):
                logger.error("Message must be a dictionary")
                return False
                
            if "name" not in message:
                logger.error("Message must contain a 'name' field")
                return False
                
            # Add message ID and timestamp if not present
            message = message.copy()  # Don't modify the original message
            if "id" not in message:
                message["id"] = str(uuid.uuid4())
                
            if "arguments" not in message:
                message["arguments"] = {}
                
            if "timestamp" not in message["arguments"]:
                message["arguments"]["timestamp"] = datetime.utcnow().isoformat()
            
            logger.debug(f"Sending message: {message}")
            
            # Save the message to local storage if enabled
            if self.storage:
                try:
                    # Convert message to Message model
                    msg = Message(
                        id=message['id'],
                        role=MessageRole.ASSISTANT,  # This is an outgoing message from the assistant
                        content=json.dumps(message),
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
            
            # Broadcast the message to WebSocket clients
            if self.server and hasattr(self.server, 'broadcast_message'):
                try:
                    # Run the broadcast in the server's event loop
                    if hasattr(self.server, 'loop') and self.server.loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            self.server.broadcast_message(message),
                            self.server.loop
                        )
                        # Wait for the broadcast to complete with a timeout
                        return future.result(timeout=5.0)
                    else:
                        logger.warning("Server event loop is not running")
                        return False
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")
                    return False
            else:
                logger.warning("Server not available for broadcasting")
                return True  # Still return True if server is not available
            
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            return False
            
    def is_running(self):
        """Check if the server is running"""
        return self.running and bool(self.server)

    def get_messages(self, offset: int = 0, limit: int = 10, desc: bool = True) -> List[Dict[str, Any]]:
        """
        Get stored messages.
        
        Args:
            offset: Number of messages to skip
            limit: Maximum number of messages to return
            desc: Whether to sort in descending order (newest first)
            
        Returns:
            List of message dictionaries
        """
        if not self.storage:
            logger.warning("Local storage is not enabled")
            return []
        return self.storage.get_messages(offset, limit, desc)
    
    def save_memory(self, memory_type: Union[MemoryType, str], content: str) -> bool:
        """
        Save a memory.
        
        Args:
            memory_type: Type of memory (short_term or long_term)
            content: Content of the memory
            
        Returns:
            bool: True if the memory was saved successfully
        """
        if not self.storage:
            logger.warning("Local storage is not enabled")
            return False
            
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType(memory_type)
            except ValueError:
                logger.error(f"Invalid memory type: {memory_type}")
                return False
                
        memory = Memory(
            type=memory_type,
            content=content,
            datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return self.storage.save_memory(memory)
    
    def get_latest_memory(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent memory from storage.
        
        Returns:
            Optional[Dict[str, Any]]: The most recent memory or None if no memories exist
        """
        return self.storage.get_latest_memory()
    
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
