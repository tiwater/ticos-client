import asyncio
import json
import unittest
import time
import requests
import shutil
import os
import json
import toml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from ticos_client import TicosClient, MessageRole, SaveMode
from ticos_client.config import ConfigService


class TestTicosClient(unittest.TestCase):
    _port_counter = 10000  # Start from port 10000 to avoid conflicts

    def _create_test_config(self, config_dir: Path):
        """Create test configuration files."""
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create config.toml
        config = {
            "api": {"api_key": "test_api_key", "base_url": "http://test-api.ticos.cn"},
            "model": {"enable_memory_generation": "client", "history_conversation_length": 5},
        }

        # Write config.toml
        with open(config_dir / "config.toml", "w") as f:
            toml.dump(config, f)

        # Create empty session_config
        with open(config_dir / "session_config", "w") as f:
            json.dump({}, f)

    def setUp(self):
        # Create a temporary directory for the test database and config
        self.temp_dir = Path.home() / ".config" / "ticos" / "test"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Create test config files
        self._create_test_config(self.temp_dir)

        # Get a unique port for this test
        self.port = self._port_counter
        TestTicosClient._port_counter += 1

        # Initialize client with test config
        self.client = TicosClient(
            port=self.port, save_mode=SaveMode.EXTERNAL, tf_root_dir=self.temp_dir
        )

        # Enable local storage with the test database
        from ticos_client.storage import SQLiteStorageService

        self.storage = SQLiteStorageService()
        self.client.enable_local_storage(self.storage)

        # Start the server
        self.assertTrue(
            self.client.start(), f"Failed to start server on port {self.port}"
        )

    def tearDown(self):
        # Stop the server and clean up
        if hasattr(self, "client") and self.client:
            self.client.stop()
        if hasattr(self, "temp_dir") and self.temp_dir:
            # Remove the test directory and all its contents
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

    def test_send_and_receive_message(self):
        """Test sending and receiving a message."""
        # Set up a message handler
        received_messages = []

        def message_handler(message: Dict[str, Any]):
            received_messages.append(message)

        self.client.set_message_handler(message_handler)

        # Create a test message with all required fields - using a format that the client can process
        test_msg = {
            "type": "response.done",
            "message": {
                "id": str(int(time.time())),
                "role": "assistant",
                "content": "Hello, Ticos!",
                "created_at": datetime.utcnow().isoformat(),
            },
        }

        # Create a new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # First save a message directly to storage to test storage functionality
            from ticos_client import Message, MessageRole

            test_message = Message(
                id="test-message-id",
                role=MessageRole.ASSISTANT,
                content="Hello, Ticos!",
                item_id="test-item-id",
                datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            self.client.storage.save_message(test_message)

            # Send the message
            result = self.client.send_message(test_msg)
            self.assertTrue(result, "Failed to send message")

            # Simulate receiving the message through WebSocket
            handled = loop.run_until_complete(
                self._simulate_websocket_message(test_msg)
            )
            self.assertTrue(handled, "Message was not handled by any handler")

            # Check if the message was received by the handler
            self.assertEqual(
                len(received_messages), 1, "Message not received by handler"
            )
            self.assertEqual(
                received_messages[0].get("type"),
                "response.done",
                "Incorrect message type",
            )
            self.assertIn(
                "message", received_messages[0], "Message missing 'message' field"
            )

            # Check if the message was saved to storage
            messages = self.client.storage.get_messages()
            self.assertGreater(len(messages), 0, "No messages found in storage")

            # Find our test message in the stored messages
            test_message_found = False
            for msg in messages:
                if msg.content == "Hello, Ticos!" and msg.role == MessageRole.ASSISTANT:
                    test_message_found = True
                    break

            self.assertTrue(test_message_found, "Test message not found in storage")

        finally:
            # Clean up the event loop
            loop.close()

    def test_invalid_message(self):
        """Test sending an invalid message."""
        # Should return False for invalid messages
        self.assertFalse(self.client.send_message("not a dict"))

    async def _simulate_websocket_message(self, message: Dict[str, Any]):
        """
        Simulate receiving a WebSocket message by directly calling the handler.

        Args:
            message: The message to simulate receiving

        Returns:
            bool: True if the message was handled, False otherwise
        """
        if not hasattr(self, "client") or not hasattr(self.client, "server"):
            raise RuntimeError("Client or server not initialized")

        # Simulate WebSocket message handling
        return await self.client.server._handle_websocket_message(message, None)

    def test_message_handlers(self):
        """Test message handlers for motion and emotion messages."""
        motion_received = []
        emotion_received = []

        def motion_handler(parameters: Dict[str, Any]):
            motion_received.append(parameters)

        def emotion_handler(parameters: Dict[str, Any]):
            emotion_received.append(parameters)

        # Set up the handlers
        self.client.set_motion_handler(motion_handler)
        self.client.set_emotion_handler(emotion_handler)

        # Create a new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Simulate receiving motion message
            motion_msg = {
                "type": "response.output_item.done",
                "item": {
                    "type": "function_call",
                    "name": "motion",
                    "arguments": json.dumps({"action": "wave"}),
                },
            }
            handled = loop.run_until_complete(
                self._simulate_websocket_message(motion_msg)
            )
            self.assertTrue(handled, "Motion message was not handled")

            # Simulate receiving emotion message
            emotion_msg = {
                "type": "response.output_item.done",
                "item": {
                    "type": "function_call",
                    "name": "emotion",
                    "arguments": json.dumps({"emotion": "happy"}),
                },
            }
            handled = loop.run_until_complete(
                self._simulate_websocket_message(emotion_msg)
            )
            self.assertTrue(handled, "Emotion message was not handled")

            # Check that handlers were called with the correct parameters
            self.assertEqual(len(motion_received), 1, "Motion handler was not called")
            self.assertEqual(
                motion_received[0].get("action"), "wave", "Incorrect motion action"
            )

            self.assertEqual(len(emotion_received), 1, "Emotion handler was not called")
            self.assertEqual(
                emotion_received[0].get("emotion"), "happy", "Incorrect emotion"
            )

        finally:
            # Clean up the event loop
            loop.close()


if __name__ == "__main__":
    unittest.main()
