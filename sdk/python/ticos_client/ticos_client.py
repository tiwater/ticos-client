import asyncio
import json
import logging
import threading
import time
from datetime import datetime
import os
from pathlib import Path
from threading import Lock, Thread
from typing import Callable, Dict, Any, Optional, List, Union
from .server import UnifiedServer
from .storage import StorageService, SQLiteStorageService
from .models import Message, MessageRole, Memory, MemoryType
from .enums import SaveMode
from .config import ConfigService
from .utils import find_tf_root_directory
from .http_util import HttpUtil
import requests

logger = logging.getLogger(__name__)

from .ticos_client_interface import MessageCallbackInterface


class TicosClient(MessageCallbackInterface):
    """
    TicosClient is a Python client for the Ticos Agent system.
    It provides a unified interface for handling both HTTP and WebSocket connections,
    along with message and memory storage capabilities.
    """

    def __init__(
        self,
        port: int = 9999,
        save_mode: SaveMode = SaveMode.INTERNAL,
        tf_root_dir: str = None,
    ):
        """
        Initialize the TicosClient.

        Args:
            port: The port number for the WebSocket server
            save_mode: The save mode for storage (INTERNAL or EXTERNAL)
            tf_root_dir: The root directory of the TF card for external storage
        """
        self.port = port
        self.save_mode = save_mode
        if save_mode == SaveMode.EXTERNAL:
            if tf_root_dir:
                self.tf_root_dir = tf_root_dir
            else:
                self.tf_root_dir = find_tf_root_directory()
        else:
            self.tf_root_dir = tf_root_dir
        self.server: Optional[UnifiedServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        self.storage: Optional[StorageService] = None
        self.message_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.motion_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.emotion_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self.function_call_handler: Optional[Callable[[str, Dict[str, Any]], None]] = (
            None
        )
        self.conversation_handler: Optional[Callable[[str, str, str], None]] = None
        self.message_counter = 0  # Add message counter
        self._last_message_id = 0  # Track the last used message ID

        # Cache for audio transcript delta messages
        self._audio_transcript_cache = {"item_id": None, "message": None, "content": ""}

        # Initialize config service
        self.config_service = ConfigService(save_mode, self.tf_root_dir)
        self.context_rounds = self.config_service.get_context_rounds()
        self.date_format = "%Y-%m-%d %H:%M:%S"

        # Initialize background task management
        self._background_task_lock = threading.Lock()
        self._background_tasks = []

    def _generate_message_id(self) -> str:
        """
        Generate a unique message ID that is always increasing.

        Returns:
            str: A string representation of the message ID
        """
        current_id = int(time.time())

        # If current_id is less than or equal to the last used ID, increment the last ID
        if current_id <= self._last_message_id:
            self._last_message_id += 1
        else:
            self._last_message_id = current_id

        return str(self._last_message_id)

    def _save_cached_audio_transcript(self) -> None:
        """
        Save the cached audio transcript message to storage and reset the cache.
        """
        if (
            self._audio_transcript_cache["message"]
            and self._audio_transcript_cache["content"]
        ):
            # Update the message content with accumulated delta
            self._audio_transcript_cache["message"].content = (
                self._audio_transcript_cache["content"]
            )

            # Save to storage
            self.storage.save_message(self._audio_transcript_cache["message"])
            logger.debug(
                f"Saved accumulated audio transcript message with item_id: {self._audio_transcript_cache['item_id']}"
            )

            # Reset cache
            self._audio_transcript_cache = {
                "item_id": None,
                "message": None,
                "content": "",
            }

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
        storage_service.set_store_root_dir(self.tf_root_dir)

        try:
            storage_service.initialize()
            self.storage = storage_service
            logger.info(f"Local storage enabled: {storage_service.__class__.__name__}")

            if self.config_service.get("model.enable_memory_generation") == "client":
                # We need to update the context messages in client side
                self.update_session_config_messages()
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
        self.message_handler = handler
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

    def set_emotion_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Set the emotion handler function"""
        self.emotion_handler = handler

    def set_function_call_handler(
        self, handler: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Set the generic function call handler

        Args:
            handler: Function that takes function name and arguments as parameters
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self.function_call_handler = handler

    def set_conversation_handler(
        self, handler: Callable[[str, str, str], None]
    ) -> None:
        """
        Set the conversation handler

        Args:
            handler: Function that takes message_id (item_id), role, and content as parameters
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self.conversation_handler = handler

    def start(self):
        """
        Start the Ticos server.

        Returns:
            bool: True if server started successfully, False otherwise
        """
        if self.running:
            logger.warning("Ticos server is already running")
            return False

        # Start the server in a separate thread
        def run_server():
            try:
                self.server = UnifiedServer(
                    message_callback=self,
                    port=self.port,
                    storage_service=self.storage,
                )
                import uvicorn

                config = uvicorn.Config(
                    self.server.app, host="0.0.0.0", port=self.port, log_level="info"
                )
                self._server = uvicorn.Server(config)
                self.running = True
                self._server.run()
            except Exception as e:
                logger.error(f"Failed to start server: {e}")
                self.running = False

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Check server status by making a test request
        try:
            for _ in range(10):  # Retry for up to 1 second
                try:
                    response = requests.get(f"http://localhost:{self.port}/health")
                    if response.status_code == 200:
                        logger.info(f"Ticos server started on port {self.port}")
                        return True
                except requests.exceptions.ConnectionError:
                    time.sleep(0.1)
            return False
        except Exception as e:
            logger.error(f"Error checking server status: {e}")
            return False

    def stop(self):
        """Stop the server and clean up resources."""
        if not self.running:
            return

        logger.info("Stopping Ticos server...")
        self.running = False

        try:
            # Signal the server to shut down gracefully
            if hasattr(self, "server") and self.server:
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
            if hasattr(self, "server_thread") and self.server_thread.is_alive():
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

            logger.debug(f"Sending message: {message}")

            # Send message directly using WebSocket
            if self.server and hasattr(self.server, "broadcast_message"):
                try:
                    # Create a new event loop for this operation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Run the broadcast coroutine
                    loop.run_until_complete(self.server.broadcast_message(message))
                    loop.close()
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
            bool: True if the message was handled by any handler
        """
        if not isinstance(message, dict):
            logger.warning(f"Invalid message format: {message}")
            return False

        try:
            # Save the message to local storage if enabled
            if self.storage:
                try:
                    text_message = False
                    # Process different message types
                    msg_type = message.get("type")

                    # Handle conversation.item.created - user message
                    if msg_type == "conversation.item.created":
                        item = message.get("item", {})
                        if item.get("type") == "message" and item.get("role") == "user":
                            # Check if content contains input_audio
                            content_list = item.get("content", [])
                            for content in content_list:
                                if content.get("type") == "input_audio":
                                    # Save as user message with empty content (will be updated later)
                                    msg = Message(
                                        id=self._generate_message_id(),
                                        role=MessageRole.USER,
                                        content="",  # Empty content, will be updated when transcription arrives
                                        item_id=item.get(
                                            "id"
                                        ),  # Save the item_id for later reference
                                        datetime=datetime.now().strftime(
                                            self.date_format
                                        ),
                                    )
                                    logger.debug(
                                        f"Saving initial user message with item_id: {item.get('id')}"
                                    )
                                    self.storage.save_message(msg)

                                    # Call conversation handler if available
                                    if (
                                        hasattr(self, "conversation_handler")
                                        and self.conversation_handler
                                    ):
                                        self.conversation_handler(
                                            item.get("id"), MessageRole.USER, ""
                                        )
                                    break

                    # Handle conversation.item.input_audio_transcription.completed - update user message
                    elif (
                        msg_type
                        == "conversation.item.input_audio_transcription.completed"
                    ):
                        item_id = message.get("item_id")
                        transcript = message.get("transcript", "")

                        if item_id:
                            # Find the message with this item_id using the new method
                            msg = self.storage.get_message_by_item_id(item_id)
                            if msg:
                                # Update the message with the transcript
                                msg.content = transcript
                                self.storage.update_message(msg.id, msg)
                                logger.debug(
                                    f"Updated user message with transcript for item_id: {item_id}"
                                )

                                # Call conversation handler if available
                                if (
                                    hasattr(self, "conversation_handler")
                                    and self.conversation_handler
                                ):
                                    self.conversation_handler(
                                        item_id, MessageRole.USER, transcript
                                    )
                            else:
                                logger.warning(
                                    f"No message found with item_id: {item_id} for transcript update"
                                )

                    # Handle response.done - assistant message
                    elif msg_type == "response.done":
                        # First, save any cached audio transcript message
                        if (
                            self._audio_transcript_cache["item_id"]
                            and self._audio_transcript_cache["message"]
                        ):
                            self._save_cached_audio_transcript()
                            text_message = True

                    # Handle response.audio_transcript.delta - assistant message delta
                    elif msg_type == "response.audio_transcript.delta":
                        item_id = message.get("item_id")
                        delta = message.get("delta", "")
                        text_message = False

                        # Process only non-empty deltas
                        if delta and item_id:
                            # Call conversation handler if available
                            if (
                                hasattr(self, "conversation_handler")
                                and self.conversation_handler
                            ):
                                self.conversation_handler(
                                    item_id, MessageRole.ASSISTANT, delta
                                )

                            # Check if we need to save the previous cached message
                            if (
                                self._audio_transcript_cache["item_id"]
                                and self._audio_transcript_cache["item_id"] != item_id
                            ):
                                # Save previous cached message before starting a new one
                                self._save_cached_audio_transcript()
                                text_message = True

                            # Create a new message if this is the first delta for this item_id
                            if (
                                not self._audio_transcript_cache["item_id"]
                                or self._audio_transcript_cache["item_id"] != item_id
                            ):
                                # This is the first delta for this item_id
                                self._audio_transcript_cache["item_id"] = item_id
                                self._audio_transcript_cache["message"] = Message(
                                    id=self._generate_message_id(),
                                    role=MessageRole.ASSISTANT,
                                    content="",  # Will be updated when saving
                                    item_id=item_id,
                                    datetime=datetime.now().strftime(self.date_format),
                                )
                                self._audio_transcript_cache["content"] = delta
                            else:
                                # Append to existing content
                                self._audio_transcript_cache["content"] += delta

                    # For other message types, don't store
                    else:
                        text_message = False

                    # Check if we need to generate a memory
                    if text_message and not msg_type == "conversation.item.created":
                        # Only proceed if memory generation is enabled in config
                        if (
                            self.config_service.get("model.enable_memory_generation")
                            == "client"
                        ):
                            self.message_counter += 1
                            logger.debug(f"Message counter: {self.message_counter}")
                            if self.message_counter * 2 >= self.context_rounds:
                                self.message_counter = 0  # Reset counter
                                # Start memory generation and session update in background
                                self._run_in_background(
                                    self._generate_memory_and_update_session,
                                    "memory_generation",
                                )
                except Exception as e:
                    logger.error(
                        f"Failed to save message to storage: {e}", exc_info=True
                    )

            # Handle different function calls
            overall_handlers_called = False

            # Handle base message types with the message handler
            if hasattr(self, "message_handler") and self.message_handler:
                self.message_handler(message)
                overall_handlers_called = True

            # Handle function call responses
            if message.get("type") == "response.output_item.done":
                item = message.get("item", {})
                if item.get("type") == "function_call":
                    function_name = item.get("name", "")
                    try:
                        # Try to parse arguments as JSON, fallback to empty dict if invalid
                        args = json.loads(item.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                        logger.warning(
                            f"Invalid JSON arguments in function call: {item.get('arguments')}"
                        )

                    handlers_called = False

                    if (
                        function_name in ["motion", "motion_and_emotion"]
                        and hasattr(self, "motion_handler")
                        and self.motion_handler
                    ):
                        self.motion_handler(args)
                        handlers_called = True

                    if (
                        function_name in ["emotion", "motion_and_emotion"]
                        and hasattr(self, "emotion_handler")
                        and self.emotion_handler
                    ):
                        self.emotion_handler(args)
                        handlers_called = True

                    # Handle other function calls with the generic function call handler
                    if (
                        not handlers_called
                        and hasattr(self, "function_call_handler")
                        and self.function_call_handler
                    ):
                        self.function_call_handler(function_name, args)
                        handlers_called = True

                    if handlers_called:
                        overall_handlers_called = True

            return overall_handlers_called

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return False

    def generate_memory(self) -> None:
        """
        Generate a memory from recent conversation history.
        This is called after a certain number of messages have been processed.
        """
        if not self.storage:
            return

        try:
            if not self.storage:
                return

            # Get the latest messages
            messages = self.storage.get_messages(0, self.context_rounds, True)

            # Get the latest memory for context
            latest_memory = self.storage.get_latest_memory()
            last_memory_content = latest_memory["content"] if latest_memory else ""

            # Use HttpUtil to call the summarization API
            memory_content = HttpUtil.summarize_conversation(
                reversed(messages), last_memory_content, self.config_service
            )

            if memory_content:
                # Save the new memory
                memory = Memory(
                    type=MemoryType.LONG_TERM,
                    content=memory_content,
                    datetime=datetime.now().strftime(self.date_format),
                )
                self.storage.save_memory(memory)
                logger.info(f"Generated new memory: {memory_content}")
        except Exception as e:
            logger.error(f"Error generating memory: {e}", exc_info=True)

    def _generate_memory_and_update_session(self):
        """
        Generate memory and update session config in one go.
        This method is designed to run in a background thread.
        """
        try:
            self.generate_memory()
            self.update_session_config_messages()
        except Exception as e:
            logger.error(f"Error in background task: {e}", exc_info=True)

    def _run_in_background(self, func, task_name):
        """
        Run a function in a background thread.

        Args:
            func: The function to run
            task_name: Name of the task for logging
        """

        def task_wrapper():
            try:
                logger.debug(f"Starting background task: {task_name}")
                func()
                logger.debug(f"Completed background task: {task_name}")
            except Exception as e:
                logger.error(
                    f"Error in background task {task_name}: {e}", exc_info=True
                )
            finally:
                with self._background_task_lock:
                    self._background_tasks = [
                        t for t in self._background_tasks if t.is_alive()
                    ]

        thread = Thread(
            target=task_wrapper, daemon=True, name=f"TicosClient_{task_name}"
        )
        thread.start()

        with self._background_task_lock:
            # Clean up finished tasks
            self._background_tasks = [t for t in self._background_tasks if t.is_alive()]
            self._background_tasks.append(thread)

    def update_session_config_messages(self):
        """
        Update the session_config file with the latest conversation messages.
        This ensures that the agent has context when restarted.
        """
        if not self.storage:
            logger.warning(
                "Cannot update session_config messages: storage not initialized"
            )
            return

        try:
            # Get the latest memory
            latest_memory = self.storage.get_latest_memory()
            last_memory_content = latest_memory["content"] if latest_memory else ""

            # Get the latest messages
            messages = self.storage.get_messages(0, self.context_rounds, True)

            # Prepare message list for session_config
            session_messages = []

            # Add conversation messages
            message_count = 0

            for message in reversed(messages):

                try:
                    # Extract content from message
                    content = ""
                    msg_content = message.content

                    if isinstance(msg_content, str):
                        content = msg_content
                    else:
                        content = str(msg_content)

                    if content:
                        session_messages.append(
                            {"role": message.role.value, "content": content}
                        )
                        message_count += 1

                except Exception as e:
                    logger.warning(f"Error processing message for session_config: {e}")

            # Ensure the last message is from assistant
            while session_messages and session_messages[-1]["role"] != "assistant":
                session_messages.pop()

            # Add memory message if available
            # if last_memory_content:
            #     memory_message = {
            #         "role": "user",
            #         "content": f"这是你总结的我们之前沟通的记忆: \n```{last_memory_content}```\n请基于此以及我们最近的会话继续和我交流：",
            #     }

            #     # 如果 session_messages 的第一条 role 为 user，则替换它
            #     if session_messages and session_messages[0]["role"] == "user":
            #         session_messages[0] = memory_message
            #     else:
            #         # 否则将记忆消息插入到最前面
            #         session_messages.insert(0, memory_message)

            # Change the memory to last message
            if last_memory_content:
                memory_message = {
                    "role": "user",
                    "content": f"这是你总结的我们之前沟通的记忆: \n```{last_memory_content}```\n请基于此以及我们最近的会话继续和我交流：",
                }

                session_messages.append(memory_message)

                session_messages.append(
                    {"role": "assistant", "content": "OK"}
                )

            # Update session_config file
            self._update_session_config_file(session_messages)

        except Exception as e:
            logger.error(f"Error updating session_config messages: {e}")

    def _update_session_config_file(self, messages):
        """
        Update the session_config file with the provided messages.
        Uses a safe write approach (write to temp file, then rename).

        Args:
            messages: List of message objects to write to the session_config
        """
        try:
            # Path to session_config
            session_config_path = Path.home() / ".config" / "ticos" / "session_config"

            # Read current session_config
            if not session_config_path.exists():
                logger.warning(f"Session config file not found: {session_config_path}")
                return

            with open(session_config_path, "r") as f:
                session_config = json.load(f)

            # Update messages under model.messages.nobody
            if "model" not in session_config:
                session_config["model"] = {}
                
            # If messages is a list, convert to dict format with 'nobody' key
            if "messages" not in session_config["model"] or isinstance(session_config["model"]["messages"], list):
                session_config["model"]["messages"] = {"nobody": messages}
            else:
                # It's already a dict, update the 'nobody' key
                session_config["model"]["messages"]["nobody"] = messages

            # Write to temporary file
            temp_path = session_config_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(session_config, f, indent=2, ensure_ascii=False)

            # Rename to overwrite original
            temp_path.replace(session_config_path)
            logger.info(f"Updated session_config with {len(messages)} messages")

        except Exception as e:
            logger.error(f"Error writing session_config file: {e}")

    def _summarize_conversation(
        self, messages: List[Dict[str, Any]], last_memory: str
    ) -> str:
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
                    # Convert Message object to dictionary
                    content = (
                        json.loads(msg.content)
                        if isinstance(msg.content, str)
                        else msg.content
                    )
                    if isinstance(content, dict) and "arguments" in content:
                        if "content" in content["arguments"]:
                            contents.append(
                                f"{msg.role.value}: {content['arguments']['content']}"
                            )
                        elif "text" in content["arguments"]:
                            contents.append(
                                f"{msg.role.value}: {content['arguments']['text']}"
                            )
                except Exception as e:
                    logger.warning(f"Error processing message for summarization: {e}")

            if not contents:
                return ""

            # Simple summarization: combine the messages
            summary = "Recent conversation: " + "; ".join(
                contents[-3:]
            )  # Just take the last 3 messages

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
        print(
            f"[DefaultMessageHandler] Received message: {json.dumps(message, indent=2)}"
        )
