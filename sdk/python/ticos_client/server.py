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

from .models import (
    Message,
    Memory,
    MessageRequest,
    MessageResponse,
    MessagesResponse,
    MessageRole,
)
from .storage import StorageService
from .ticos_client_interface import MessageCallbackInterface

logger = logging.getLogger(__name__)


class UnifiedServer:
    """Unified server that handles both HTTP and WebSocket connections."""

    def __init__(
        self,
        message_callback: MessageCallbackInterface,
        port: int = 9999,
        storage_service: Optional[StorageService] = None,
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

        @self.app.websocket("/realtime")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await self._register_websocket(websocket)

            try:
                while True:
                    try:
                        # Handle different message types
                        message = await websocket.receive()
                        logger.debug(
                            f"[WebSocket] Received message: {json.dumps(message, default=str, ensure_ascii=False)}"
                        )

                        # Handle text messages (JSON)
                        if "text" in message:
                            try:
                                data = json.loads(message["text"])
                                logger.debug(
                                    f"[WebSocket] Parsed message data: {json.dumps(data, default=str, ensure_ascii=False, indent=2)}"
                                )
                                await self._handle_websocket_message(data, websocket)
                            except json.JSONDecodeError as je:
                                logger.error(
                                    f"[WebSocket] Failed to parse JSON: {message['text']}",
                                    exc_info=True,
                                )
                            except Exception as e:
                                logger.error(
                                    f"[WebSocket] Error handling text message: {str(e)}",
                                    exc_info=True,
                                )
                        # Handle binary messages containing JSON data
                        elif "bytes" in message:
                            try:
                                # Convert bytes to string and clean up the binary string representation
                                binary_data = message["bytes"]

                                # Handle different binary message formats
                                if isinstance(binary_data, bytes):
                                    # If it's actual bytes, decode it
                                    try:
                                        # Try UTF-8 decoding first
                                        json_str = binary_data.decode("utf-8")
                                    except UnicodeDecodeError:
                                        # If UTF-8 fails, try with error handling
                                        json_str = binary_data.decode(
                                            "utf-8", errors="replace"
                                        )

                                    # Clean up common binary string artifacts
                                    json_str = json_str.strip("'")

                                    try:
                                        # Try to parse the JSON
                                        data = json.loads(json_str)
                                        logger.debug(
                                            f"[WebSocket] Parsed binary JSON: {json.dumps(data, ensure_ascii=False, indent=2)}"
                                        )
                                        await self._handle_websocket_message(
                                            data, websocket
                                        )
                                    except json.JSONDecodeError as je:
                                        logger.error(
                                            f"[WebSocket] Failed to parse binary JSON: {json_str}",
                                            exc_info=True,
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"[WebSocket] Error processing binary message: {str(e)}",
                                            exc_info=True,
                                        )
                                else:
                                    logger.warning(
                                        f"[WebSocket] Unexpected binary message format: {type(binary_data)}"
                                    )

                            except Exception as e:
                                logger.error(
                                    f"[WebSocket] Error processing binary message: {str(e)}",
                                    exc_info=True,
                                )
                        # Handle close messages
                        elif message.get("type") == "websocket.disconnect":
                            logger.info("[WebSocket] Client disconnected")
                            break
                        else:
                            logger.warning(
                                f"[WebSocket] Unhandled message type: {message.keys()}"
                            )

                    except WebSocketDisconnect as wd:
                        logger.info(f"[WebSocket] Client disconnected: {str(wd)}")
                        break
                    except Exception as e:
                        logger.error(
                            f"[WebSocket] Unexpected error: {str(e)}", exc_info=True
                        )
                        break
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                await self._unregister_websocket(websocket)

    async def _register_websocket(self, websocket: WebSocket):
        """Register a new WebSocket connection"""
        with self.websocket_lock:
            self.websocket_connections.append(websocket)
            logger.info(
                f"New WebSocket connection. Total connections: {len(self.websocket_connections)}"
            )

    async def _unregister_websocket(self, websocket: WebSocket):
        """Unregister a WebSocket connection"""
        with self.websocket_lock:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
                logger.info(
                    f"WebSocket connection closed. Remaining connections: {len(self.websocket_connections)}"
                )

    def _should_process_message(self, message: Dict[str, Any]) -> bool:
        """
        Determine if a message should be processed based on its type and content.

        Args:
            message: The incoming message

        Returns:
            bool: True if the message should be processed, False otherwise
        """
        msg_type = message.get("type")
        if not msg_type:
            return False

        # Always process these message types
        allowed_types = {
            "conversation.item.created",
            "response.created",
            "conversation.item.input_audio_transcription.completed",
            "response.output_item.done",
            "response.audio_transcript.delta",
            "response.done",
            "response.audio.delta",
        }

        if msg_type in allowed_types:
            return True

        return False

    async def _handle_websocket_message(
        self, message: Dict[str, Any], websocket: WebSocket
    ):
        """
        Handle incoming WebSocket message with filtering.

        Only processes specific message types and handles audio delta deduplication.
        """
        try:
            if not isinstance(message, dict):
                logger.warning(f"Invalid message type: {type(message)}")
                return False

            # Check if we should process this message
            if not self._should_process_message(message):
                return False

            # Call the registered message callback
            if self.message_callback:
                handled = self.message_callback.handle_message(message)
                if not handled:
                    logger.warning(f"Message not handled: {message.get('type')}")
                return handled

            logger.warning("No message callback registered")
            return False

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
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
        return hasattr(self, "_is_running") and self._is_running

    async def _startup(self):
        """Startup the FastAPI server"""
        config = uvicorn.Config(
            self.app, host="0.0.0.0", port=self.port, log_level="info"
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
