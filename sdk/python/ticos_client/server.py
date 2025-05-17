import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Union

import uvicorn

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .models import Message, Memory, MessageRequest, MessageResponse, MessagesResponse, MessageRole
from .storage import StorageService
from .ticos_client_interface import MessageCallbackInterface

logger = logging.getLogger(__name__)

class UnifiedServer:
    """Unified server that handles both HTTP and WebSocket connections."""
    
    def __init__(
        self,
        message_callback: MessageCallbackInterface,
        port: int = 9999,
        storage_service: Optional[StorageService] = None
    ):  
        self.port = port
        self.storage = storage_service
        self.ticos_client = None
        self.app = FastAPI(title="Ticos Agent Server")
        self._setup_middleware()
        self._setup_routes()
        self.websocket_connections: List[WebSocket] = []
        self.websocket_lock = threading.Lock()
        self._server = None
        self._should_exit = False
        self.message_callback = message_callback
        
        # Ensure message_callback is properly initialized
        if not isinstance(message_callback, MessageCallbackInterface):
            raise ValueError("message_callback must implement MessageCallbackInterface")
    
    def _setup_middleware(self):
        """Set up CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Set up HTTP and WebSocket routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "ok"}
                
        @self.app.get("/memories/latest")
        async def get_latest_memories(count: int = 4):
            """
            Get the latest memories (messages) from storage.
            
            Args:
                count: Number of latest messages to return (default: 4)
                
            Returns:
                List of message objects with role and content fields
            """
            try:
                if not self.storage:
                    raise HTTPException(status_code=500, detail="Storage service not available")
                
                # Get the latest messages (in descending order by datetime)
                messages = self.storage.get_messages(offset=0, limit=count, desc=True)
                
                # Return the full message content
                result = []
                for msg in reversed(messages):  # Reverse to get oldest first
                    try:
                        content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                        result.append({
                            "role": msg.role.value,
                            "content": content  # Return the full content
                        })
                    except Exception as e:
                        logger.warning(f"Error processing message {msg.id}: {e}")
                        continue
                
                return result
                
            except Exception as e:
                logger.error(f"Error getting latest memories: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/realtime")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await self._register_websocket(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        message = json.loads(data)
                        await self._handle_websocket_message(message, websocket)
                    except json.JSONDecodeError:
                        logger.error("Received invalid JSON")
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            finally:
                await self._unregister_websocket(websocket)
    
    async def _register_websocket(self, websocket: WebSocket):
        """Register a new WebSocket connection"""
        with self.websocket_lock:
            self.websocket_connections.append(websocket)
            logger.info(f"New WebSocket connection. Total connections: {len(self.websocket_connections)}")
    
    async def _unregister_websocket(self, websocket: WebSocket):
        """Unregister a WebSocket connection"""
        with self.websocket_lock:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
                logger.info(f"WebSocket connection closed. Remaining connections: {len(self.websocket_connections)}")
    
    async def _handle_websocket_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Handle incoming WebSocket message"""
        try:
            if not isinstance(message, dict):
                logger.warning(f"Invalid message type: {type(message)}")
                return False
                
            # Call the registered message callback
            if self.message_callback:
                handled = self.message_callback.handle_message(message)
                if not handled:
                    logger.warning(f"Message not handled: {message.get('name')}")
                return handled
                
            logger.warning("No message callback registered")
            return False
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return False
            
    
    async def broadcast_message(self, message: Dict[str, Any]) -> bool:
        """
        Broadcast a message to all connected WebSocket clients.
        
        Args:
            message: The message to broadcast
            
        Returns:
            bool: True if the message was sent to at least one client
        """
        if not self.websocket_connections:
            return False
            
        message_str = json.dumps(message)
        sent_to_any = False
        with self.websocket_lock:
            for connection in self.websocket_connections.copy():
                try:
                    await connection.send_text(message_str)
                    sent_to_any = True  # At least one send succeeded
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    # Remove the connection if there's an error
                    try:
                        await self._unregister_websocket(connection)
                    except Exception as e:
                        logger.error(f"Error unregistering WebSocket: {e}")
        
        return sent_to_any
    
    def is_running(self) -> bool:
        """Check if the server is running"""
        # In a real implementation, we would check if the server is actually running
        # For now, we'll just return True if the server has been started
        return hasattr(self, '_is_running') and self._is_running

    async def _startup(self):
        """Startup the FastAPI server"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        self._server = uvicorn.Server(config)
        await self._server.serve()

    def run(self):
        """Run the FastAPI server"""
        self._is_running = True
        self._should_exit = False
        try:
            asyncio.run(self._startup())
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            self._is_running = False
            self._should_exit = True
    
    async def shutdown(self):
        """Shutdown the server gracefully"""
        if self._server:
            self._should_exit = True
            self._server.should_exit = True
            # Close all WebSocket connections
            with self.websocket_lock:
                for connection in self.websocket_connections:
                    try:
                        await connection.close()
                    except Exception as e:
                        logger.error(f"Error closing WebSocket connection: {e}")
                self.websocket_connections.clear()
            logger.info("Server shutdown complete")
