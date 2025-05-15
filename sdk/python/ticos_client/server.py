import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Union

import uvicorn

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .models import Message, Memory, MessageRequest, MessageResponse, MessagesResponse
from .storage import StorageService

logger = logging.getLogger(__name__)

class UnifiedServer:
    """Unified server that handles both HTTP and WebSocket connections."""
    
    def __init__(
        self,
        port: int = 9999,
        storage_service: Optional[StorageService] = None,
        message_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
        motion_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
        emotion_handler: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.port = port
        self.storage = storage_service
        self.message_handler = message_handler
        self.motion_handler = motion_handler
        self.emotion_handler = emotion_handler
        self.app = FastAPI(title="Ticos Agent Server")
        self._setup_middleware()
        self._setup_routes()
        self.websocket_connections: List[WebSocket] = []
        self.websocket_lock = threading.Lock()
        self._server = None
        self._should_exit = False
    
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
                
                # Convert to the required format
                result = []
                for msg in reversed(messages):  # Reverse to get oldest first
                    try:
                        content = json.loads(msg["content"]) if isinstance(msg["content"], str) else msg["content"]
                        # If content is a dict with 'content' key, use that, otherwise use the whole content
                        content_str = content.get("content") if isinstance(content, dict) else str(content)
                        result.append({
                            "role": msg["role"],
                            "content": content_str
                        })
                    except Exception as e:
                        logger.warning(f"Error processing message {msg.get('id')}: {e}")
                        continue
                
                return result
                
            except Exception as e:
                logger.error(f"Error getting latest memories: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
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
            # Save the message if storage is available
            if self.storage:
                msg = Message(
                    id=str(uuid.uuid4()),
                    role=MessageRole.USER,
                    content=json.dumps(message),
                    datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                self.storage.save_message(msg)
            
            # Handle the message
            await self._handle_message(message)
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await websocket.send_json({"status": "error", "message": str(e)})
    
    async def _handle_message(self, message: Dict[str, Any]) -> bool:
        """
        Handle incoming message.
        
        Args:
            message: The incoming message
            
        Returns:
            bool: True if the message was handled by any handler, False otherwise
        """
        if not isinstance(message, dict):
            logger.error(f"Invalid message format: {message}")
            return False
            
        message_name = message.get("name")
        arguments = message.get("arguments", {})
        handled = False
        
        try:
            # Log the received message for debugging
            logger.debug(f"Handling message: {message_name} with args: {arguments}")
            
            # Call the appropriate handler
            if message_name == "motion":
                if self.motion_handler:
                    self.motion_handler(arguments)
                    handled = True
                    logger.debug("Called motion handler")
                else:
                    logger.warning("No motion handler registered")
            elif message_name == "emotion":
                if self.emotion_handler:
                    self.emotion_handler(arguments)
                    handled = True
                    logger.debug("Called emotion handler")
                else:
                    logger.warning("No emotion handler registered")
            elif message_name == "motion_and_emotion":
                if self.motion_handler:
                    self.motion_handler(arguments)
                    handled = True
                    logger.debug("Called motion handler (from motion_and_emotion)")
                if self.emotion_handler:
                    self.emotion_handler(arguments)
                    handled = handled or bool(self.emotion_handler)
                    logger.debug("Called emotion handler (from motion_and_emotion)")
            elif self.message_handler:
                self.message_handler(message)
                handled = True
                logger.debug("Called generic message handler")
            else:
                logger.info(f"Received unhandled message: {message}")
                
            return handled
            
        except Exception as e:
            logger.error(f"Error handling message {message_name}: {e}", exc_info=True)
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
