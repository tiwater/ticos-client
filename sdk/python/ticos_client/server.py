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


class StartupErrorLogHandler(logging.Handler):
    def __init__(self, unified_server_instance):
        super().__init__()
        self.unified_server = unified_server_instance
        self.setLevel(logging.ERROR)

    def emit(self, record):
        msg = record.getMessage()
        # Check for specific error messages related to startup failure
        if "Address already in use" in msg or \
           "[Errno 48]" in msg or \
           "error while attempting to bind" in msg:
            # Capture the first relevant error log
            if not self.unified_server._captured_startup_error_log:
                self.unified_server._captured_startup_error_log = msg


class UnifiedServer:
    """Unified server that handles both HTTP and WebSocket connections."""

    def __init__(
        self,
        message_callback: Optional[MessageCallbackInterface] = None,
        port: int = 9999,
        storage_service: Optional[StorageService] = None,
    ):
        self.startup_error_message: Optional[str] = None
        self._captured_startup_error_log: Optional[str] = None
        self._server: Optional[uvicorn.Server] = None # Will hold the uvicorn.Server instance
        self.port = port
        self.storage = storage_service
        self.ticos_client = None
        self.app = FastAPI(title="Ticos Agent Server")
        self._setup_middleware()
        self._setup_routes()
        self.websocket_connections: List[WebSocket] = []
        self.websocket_lock = threading.Lock()
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
                        # logger.debug(
                        #     f"[WebSocket] Received message: {json.dumps(message, default=str, ensure_ascii=False)}"
                        # )

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
        """Register a new WebSocket connection and trigger memory update"""
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
            "response.video.done",
            "conversation.created",
            "health.status"
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

    async def _serve_uvicorn(self):
        """Configures and runs the uvicorn server."""
        config = uvicorn.Config(
            self.app, host="0.0.0.0", port=self.port, log_level="info"
        )
        # self._server is the uvicorn.Server instance
        # It's crucial that self._server is assigned before await self._server.serve()
        # so TicosClient can potentially inspect it even if serve() exits quickly.
        self._server = uvicorn.Server(config)
        
        # The self._server.started flag will be set by uvicorn internally 
        # if its startup sequence (binding, etc.) is successful, 
        # before serve() blocks for the main loop or exits due to error.
        await self._server.serve() # This can raise SystemExit if startup fails critically

    def run(self):
        """Runs the FastAPI server and handles startup error detection."""
        self._is_running = True # Optimistic, TicosClient will verify post-startup attempt
        self._should_exit = False
        self.startup_error_message = None # Reset for this run
        self._captured_startup_error_log = None # Reset for this run

        uvicorn_error_logger = logging.getLogger("uvicorn.error")
        log_handler = StartupErrorLogHandler(self)
        uvicorn_error_logger.addHandler(log_handler)

        try:
            asyncio.run(self._serve_uvicorn())
            # If asyncio.run completes without SystemExit, uvicorn's serve() completed.
            # This usually means a clean shutdown after successful run.
            if self._server and self._server.started:
                logger.info(f"Uvicorn server on port {self.port} shut down gracefully.")
            elif not self.startup_error_message: # Not started and no specific error caught
                # This case implies serve() returned but server wasn't 'started', e.g. lifespan.shutdown() called early
                self.startup_error_message = f"Server on port {self.port} exited without confirming startup and no specific error was logged."
                logger.warning(self.startup_error_message)
                if hasattr(self.message_callback, 'handle_message') and self.message_callback:
                    self.message_callback.handle_message({
                        'code': 'EXECUTER_ERROR',
                        'message': self.startup_error_message,
                        'type': 'health.status'
                    })

        except SystemExit:
            # Expected if uvicorn's startup fails critically (e.g., port in use) and calls sys.exit(1)
            if self._server is not None and not self._server.started:
                # It's a startup failure.
                if self._captured_startup_error_log:
                    specific_error = self._captured_startup_error_log
                    if "address already in use" in specific_error.lower() or \
                       "[errno 48]" in specific_error.lower() or \
                       "error while attempting to bind" in specific_error.lower():
                        self.startup_error_message = f"Server startup failed: Port {self.port} is already in use. (Detail: {specific_error})"
                    else:
                        self.startup_error_message = f"Server startup failed: {specific_error}"
                else:
                    self.startup_error_message = f"Server critical startup error on port {self.port} (e.g., port in use) and exited."
                
                logger.error(self.startup_error_message)
                if hasattr(self.message_callback, 'handle_message') and self.message_callback:
                    self.message_callback.handle_message({
                        'code': 'EXECUTER_ERROR',
                        'message': self.startup_error_message,
                        'type': 'health.status'
                    })
            # If SystemExit occurred but server was 'started', it might be a signal-based shutdown.
            # We are primarily concerned with startup failures where 'started' is false.

        except Exception as e:
            # Other unexpected errors during server run or _serve_uvicorn setup
            self.startup_error_message = f"Server runtime error on port {self.port}: {str(e)}"
            logger.error(self.startup_error_message, exc_info=True)
            if hasattr(self.message_callback, 'handle_message') and self.message_callback:
                self.message_callback.handle_message({
                    'code': 'EXECUTER_ERROR',
                    'message': self.startup_error_message,
                    'type': 'health.status'
                })
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
