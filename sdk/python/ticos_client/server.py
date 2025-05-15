import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Union

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
        
        @self.app.post("/api/messages")
        async def create_message(message: MessageRequest):
            try:
                # Save the message
                if self.storage:
                    msg = Message(
                        id=str(uuid.uuid4()),
                        role=MessageRole.USER,
                        content=json.dumps(message.dict()),
                        datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    self.storage.save_message(msg)
                
                # Handle the message
                await self._handle_message(message.dict())
                
                return {"status": "success", "message": "Message processed"}
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/messages")
        async def get_messages(offset: int = 0, limit: int = 10, desc: bool = True):
            try:
                if not self.storage:
                    raise HTTPException(status_code=500, detail="Storage service not available")
                
                messages = self.storage.get_messages(offset, limit, desc)
                return {
                    "status": "success",
                    "data": messages,
                    "total": len(messages),  # Note: This should be total count in a real implementation
                    "offset": offset,
                    "limit": limit
                }
            except Exception as e:
                logger.error(f"Error getting messages: {e}")
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
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message"""
        message_name = message.get("name")
        arguments = message.get("arguments", {})
        
        # Call the appropriate handler
        if message_name == "motion" and self.motion_handler:
            self.motion_handler(arguments)
        elif message_name == "emotion" and self.emotion_handler:
            self.emotion_handler(arguments)
        elif message_name == "motion_and_emotion":
            if self.motion_handler:
                self.motion_handler(arguments)
            if self.emotion_handler:
                self.emotion_handler(arguments)
        elif self.message_handler:
            self.message_handler(message)
        else:
            logger.info(f"Received unhandled message: {message}")
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
            
        message_str = json.dumps(message)
        with self.websocket_lock:
            for connection in self.websocket_connections.copy():
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    # Remove the connection if there's an error
                    try:
                        await self._unregister_websocket(connection)
                    except:
                        pass
    
    def run(self):
        """Run the FastAPI server"""
        import uvicorn
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
