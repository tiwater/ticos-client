import json
import logging
import threading
import time
from typing import Callable, Dict, Any, Optional, List, Union
from datetime import datetime

from .server import UnifiedServer
from .storage import StorageService, SQLiteStorageService
from .models import Message, MessageRole, Memory, MemoryType

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
        self.message_handler = handler
        logger.debug("Message handler set")

    def set_motion_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Set the motion handler function.
        
        Args:
            handler: Function that takes a motion parameters dictionary as argument
        """
        self.motion_handler = handler
        logger.debug("Motion handler set")

    def set_emotion_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Set the emotion handler function.
        
        Args:
            handler: Function that takes an emotion parameters dictionary as argument
        """
        self.emotion_handler = handler
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
            
            self.running = True
            logger.info(f"Ticos server started on port {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the server and clean up resources."""
        if not self.running:
            return
            
        self.running = False
        
        # Note: In a real implementation, we would properly shut down the FastAPI server
        # For now, we just clean up resources
        if hasattr(self, 'server_thread') and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
            
        logger.info("Ticos server stopped")
    
    def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to all connected WebSocket clients.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if the message was sent to at least one client
        """
        if not self.running or not self.server:
            logger.warning("Cannot send message: server not running")
            return False
            
        try:
            # If it's a string, try to parse it as JSON
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON message")
                    return False
            
            # Ensure the message has the required fields
            if not isinstance(message, dict) or 'name' not in message:
                logger.error("Message must be a dictionary with a 'name' field")
                return False
                
            # Add timestamp if not present
            if 'timestamp' not in message:
                message['timestamp'] = datetime.utcnow().isoformat()
            
            # Broadcast the message to all WebSocket clients
            self.server.broadcast_message(message)
            
            # Save the message to storage if available
            if self.storage:
                msg = Message(
                    id=str(message.get('id', str(uuid.uuid4()))),
                    role=MessageRole.USER,
                    content=json.dumps(message),
                    datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                self.storage.save_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
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
        Get the latest saved memory.
        
        Returns:
            Memory dictionary or None if no memories exist
        """
        if not self.storage:
            logger.warning("Local storage is not enabled")
            return None
            
        return self.storage.get_latest_memory()


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
