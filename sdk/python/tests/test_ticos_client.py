import asyncio
import json
import os
import tempfile
import unittest
import uuid
import requests
from datetime import datetime
from typing import Dict, Any

from ticos_client import TicosClient, MessageRole


class TestTicosClient(unittest.TestCase):
    _port_counter = 10000  # Start from port 10000 to avoid conflicts
    
    def setUp(self):
        # Create a temporary directory for the test database
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Get a unique port for this test
        self.port = self._port_counter
        TestTicosClient._port_counter += 1
        
        # Initialize the client with test settings
        self.client = TicosClient(port=self.port, save_mode="internal")
        
        # Enable local storage with the test database
        from ticos_client.storage import SQLiteStorageService
        self.storage = SQLiteStorageService()
        self.storage.set_store_root_dir(self.temp_dir.name)  # Use the temporary directory
        self.storage.initialize()
        self.client.enable_local_storage(self.storage)
        
        # Start the server
        self.assertTrue(self.client.start(), f"Failed to start server on port {self.port}")
        
    def tearDown(self):
        # Stop the server and clean up
        if hasattr(self, 'client') and self.client:
            self.client.stop()
        if hasattr(self, 'temp_dir') and self.temp_dir:
            self.temp_dir.cleanup()
    
    def test_send_and_receive_message(self):
        """Test sending and receiving a message."""
        # Set up a message handler
        received_messages = []
        
        def message_handler(message: Dict[str, Any]):
            received_messages.append(message)
        
        self.client.set_message_handler(message_handler)
        
        # Create a test message with all required fields
        test_msg = {
            "name": "test_message",
            "arguments": {
                "text": "Hello, Ticos!",
                "timestamp": datetime.utcnow().isoformat()
            },
            "id": str(uuid.uuid4())  # Add an ID for the test
        }
        
        # Create a new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Send the message
            self.client.handle_message(test_msg)
            result = self.client.send_message(test_msg)
            self.assertTrue(result, "Failed to send message")
            
            # Simulate receiving the message through WebSocket
            handled = loop.run_until_complete(self._simulate_websocket_message(test_msg))
            self.assertTrue(handled, "Message was not handled by any handler")
            
            # Check if the message was received by the handler
            self.assertEqual(len(received_messages), 1, "Message not received by handler")
            self.assertEqual(received_messages[0].get("name"), "test_message", "Incorrect message name")
            self.assertEqual(received_messages[0].get("arguments", {}).get("text"), 
                           "Hello, Ticos!", "Incorrect message text")
            
            # Check if the message was saved to storage
            messages = self.client.storage.get_messages()
            self.assertGreater(len(messages), 0, "No messages found in storage")
            
            # Find our test message in the stored messages
            test_message_found = False
            for msg in messages:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if isinstance(content, dict) and content.get("name") == "test_message":
                    test_message_found = True
                    self.assertEqual(content.get("arguments", {}).get("text"),
                                  "Hello, Ticos!", "Incorrect message text in storage")
                    self.assertEqual(msg.role, MessageRole.USER, "Incorrect message role in storage")
                    break
                    
            self.assertTrue(test_message_found, "Test message not found in storage")
            
        finally:
            # Clean up the event loop
            loop.close()
    
    def test_save_and_retrieve_memory(self):
        """Test sending and retrieving messages via the API."""
        # Send a test message
        test_msg = {
            "name": "test_message",
            "arguments": {
                "text": "Tell me a joke"
            }
        }
        self.client.handle_message(test_msg)
        self.assertTrue(self.client.send_message(test_msg))
        
        # Verify we can get the latest messages via the API
        response = requests.get(f"http://localhost:{self.port}/memories/latest?count=4")
        self.assertEqual(response.status_code, 200)
        messages = response.json()
        self.assertIsInstance(messages, list)
        
        # The test message should be in the latest messages
        found_test_message = False
        for msg in messages:
            content = msg.get("content", {})
            if not isinstance(content, dict):
                content = {}
            args = content.get("arguments", {})
            if args.get("text") == "Tell me a joke":
                found_test_message = True
                self.assertEqual(msg["role"], "user")
                break
        
        self.assertTrue(found_test_message, "Test message not found in latest messages")
    
    def test_invalid_message(self):
        """Test sending an invalid message."""
        # Should return False for invalid messages
        self.assertFalse(self.client.send_message("not a dict"))
        self.assertFalse(self.client.send_message({"missing_name_field": True}))
    
    async def _simulate_websocket_message(self, message: Dict[str, Any]):
        """
        Simulate receiving a WebSocket message by directly calling the handler.
        
        Args:
            message: The message to simulate receiving
            
        Returns:
            bool: True if the message was handled, False otherwise
        """
        if not hasattr(self, 'client') or not hasattr(self.client, 'server'):
            raise RuntimeError("Client or server not initialized")
            
        # Simulate WebSocket message handling
        return await self.client.server._handle_message(message)
    
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
                "name": "motion",
                "arguments": {"action": "wave"}
            }
            handled = loop.run_until_complete(self._simulate_websocket_message(motion_msg))
            self.assertTrue(handled, "Motion message was not handled")
            
            # Simulate receiving emotion message
            emotion_msg = {
                "name": "emotion",
                "arguments": {"emotion": "happy"}
            }
            handled = loop.run_until_complete(self._simulate_websocket_message(emotion_msg))
            self.assertTrue(handled, "Emotion message was not handled")
            
            # Check that handlers were called with the correct parameters
            self.assertEqual(len(motion_received), 1, "Motion handler was not called")
            self.assertEqual(motion_received[0].get("action"), "wave", "Incorrect motion action")
            
            self.assertEqual(len(emotion_received), 1, "Emotion handler was not called")
            self.assertEqual(emotion_received[0].get("emotion"), "happy", "Incorrect emotion")
            
        finally:
            # Clean up the event loop
            loop.close()


if __name__ == "__main__":
    unittest.main()
