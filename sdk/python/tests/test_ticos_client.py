import asyncio
import json
import os
import tempfile
import unittest
from datetime import datetime
from typing import Dict, Any

from ticos_client import TicosClient, MessageRole, MemoryType


class TestTicosClient(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the test database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        
        # Initialize the client with test settings
        self.client = TicosClient(port=9999)
        
        # Enable local storage with the test database
        from ticos_client.storage import SQLiteStorageService
        self.storage = SQLiteStorageService(database_url=f"sqlite:///{self.db_path}")
        self.client.enable_local_storage(self.storage)
        
        # Start the server
        self.assertTrue(self.client.start())
    
    def tearDown(self):
        # Clean up
        self.client.stop()
        self.temp_dir.cleanup()
    
    def test_send_and_receive_message(self):
        """Test sending and receiving a message."""
        # Set up a message handler
        received_messages = []
        
        def message_handler(message: Dict[str, Any]):
            received_messages.append(message)
        
        self.client.set_message_handler(message_handler)
        
        # Send a test message
        test_msg = {
            "name": "test_message",
            "arguments": {
                "text": "Hello, Ticos!",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        self.assertTrue(self.client.send_message(test_msg))
        
        # Give some time for the message to be processed
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.1))
        
        # Check if the message was received
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0]["name"], "test_message")
        self.assertEqual(received_messages[0]["arguments"]["text"], "Hello, Ticos!")
        
        # Check if the message was saved to storage
        messages = self.client.get_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], MessageRole.USER)
        self.assertEqual(json.loads(messages[0]["content"])["name"], "test_message")
    
    def test_save_and_retrieve_memory(self):
        """Test saving and retrieving a memory."""
        # Save a memory
        memory_content = "User prefers dark mode"
        self.assertTrue(self.client.save_memory(MemoryType.SHORT_TERM, memory_content))
        
        # Retrieve the latest memory
        memory = self.client.get_latest_memory()
        self.assertIsNotNone(memory)
        self.assertEqual(memory["content"], memory_content)
        self.assertEqual(memory["type"], MemoryType.SHORT_TERM.value)
        
        # Test with string memory type
        self.assertTrue(self.client.save_memory("long_term", "This is a long-term memory"))
        memory = self.client.get_latest_memory()
        self.assertEqual(memory["type"], MemoryType.LONG_TERM.value)
    
    def test_invalid_message(self):
        """Test sending an invalid message."""
        # Should return False for invalid messages
        self.assertFalse(self.client.send_message("not a dict"))
        self.assertFalse(self.client.send_message({"missing_name_field": True}))
    
    def test_message_handlers(self):
        """Test message handlers for motion and emotion messages."""
        motion_received = False
        emotion_received = False
        
        def motion_handler(parameters: Dict[str, Any]):
            nonlocal motion_received
            motion_received = True
            self.assertEqual(parameters["action"], "wave")
        
        def emotion_handler(parameters: Dict[str, Any]):
            nonlocal emotion_received
            emotion_received = True
            self.assertEqual(parameters["emotion"], "happy")
        
        self.client.set_motion_handler(motion_handler)
        self.client.set_emotion_handler(emotion_handler)
        
        # Send motion message
        self.client.send_message({
            "name": "motion",
            "arguments": {"action": "wave"}
        })
        
        # Send emotion message
        self.client.send_message({
            "name": "emotion",
            "arguments": {"emotion": "happy"}
        })
        
        # Give some time for the messages to be processed
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.1))
        
        self.assertTrue(motion_received)
        self.assertTrue(emotion_received)


if __name__ == "__main__":
    unittest.main()
