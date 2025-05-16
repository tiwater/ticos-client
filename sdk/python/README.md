# Ticos Client Python SDK

A Python SDK for the Ticos Agent system with support for both HTTP RESTful API and WebSocket connections. This SDK allows you to create applications that can send and receive messages, handle motion and emotion commands, and store messages and memories locally.

## Features

- Unified server supporting both HTTP and WebSocket connections
- Local message and memory storage using SQLite
- Asynchronous message handling
- Type hints for better development experience
- Extensible architecture with support for custom handlers

## Installation

```bash
pip install ticos-client>=0.2.0
```

## Quick Start

### Basic Usage

```python
import asyncio
from ticos_client import TicosClient, DefaultMessageHandler

class CustomMessageHandler(DefaultMessageHandler):
    def handle_message(self, message):
        print(f"Received message: {message}")
        
        if message.get('name') == 'greeting':
            name = message.get('arguments', {}).get('name', 'stranger')
            print(f"Hello, {name}!")

async def main():
    # Create and start the client
    client = TicosClient(port=9999)
    
    # Enable local storage (SQLite by default)
    client.enable_local_storage()
    
    # Set message handler
    client.set_message_handler(CustomMessageHandler().handle_message)
    
    # Start the server
    if not client.start():
        print("Failed to start server")
        return
    
    try:
        print("Server started. Press Ctrl+C to stop.")
        
        # Send a welcome message
        welcome_msg = {
            "name": "greeting",
            "arguments": {
                "name": "Ticos User"
            }
        }
        
        if client.send_message(welcome_msg):
            print("Sent welcome message")
        
        # Keep the server running
        while client.is_running():
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        client.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### TicosClient

#### Constructor

```python
client = TicosClient(port: int = 9999)
```

Creates a new Ticos client instance.

#### Methods

- `enable_local_storage(storage: Optional[StorageService] = None) -> None`
  - Enable local storage with an optional custom storage service
  - If no storage service is provided, a default SQLiteStorageService will be used

- `start() -> bool`
  - Start the HTTP and WebSocket server
  - Returns True if startup was successful

- `stop() -> None`
  - Stop the server and clean up resources

- `is_running() -> bool`
  - Check if the server is running
  - Returns True if the server is running

- `send_message(message: Dict[str, Any]) -> bool`
  - Send a message to all connected WebSocket clients
  - Returns True if the message was sent successfully

- `get_messages(offset: int = 0, limit: int = 10, desc: bool = True) -> List[Dict[str, Any]]`
  - Get stored messages
  - Returns a list of message dictionaries

- `save_memory(memory_type: Union[MemoryType, str], content: str) -> bool`
  - Save a memory
  - Returns True if the memory was saved successfully

- `get_latest_memory() -> Optional[Dict[str, Any]]`
  - Get the latest saved memory
  - Returns the memory dictionary or None if no memories exist

- `set_message_handler(handler: Callable[[dict], None])`
  - Set handler for general messages
  - handler: Function that takes a message dictionary as parameter

- `set_motion_handler(handler: Callable[[dict], None])`
  - Set handler for motion commands
  - handler: Function that takes a parameters dictionary as parameter

- `set_emotion_handler(handler: Callable[[dict], None])`
  - Set handler for emotion commands
  - handler: Function that takes a parameters dictionary as parameter

### Message Format

Messages should be dictionaries with the following structure:

```python
{
    "name": str,        # The name of the message (e.g., "motion", "emotion", "heartbeat")
    "arguments": dict  # A dictionary of parameters specific to the message type
}
```

#### Motion Message Arguments

The contents of the "arguments" object for a ticos message should be a JSON object, the exact structure of which depends on the requirement of your application.

For example, the following JSON object is a valid motion message:
```json
{
    "motion_tag": "string",     // The motion ID
    "speed": 1.0,       // Motion speed (optional, default: 1.0)
    "repeat": 1         // Number of times to repeat (optional, default: 1)
}
```

#### Emotion Message Arguments

The contents of the "arguments" object for a ticos message should be a JSON object, the exact structure of which depends on the requirement of your application.

For example, the following JSON object is a valid motion message:
```json
{
    "emotion_tag": "string",     // The emotion ID
    "intensity": 1.0,   // Emotion intensity (optional, default: 1.0)
    "duration": 2.5     // Duration in seconds (optional)
}
```

## Features

- Simple and intuitive API for sending and receiving messages
- Automatic handling of connection management
- Thread-safe operations
- Support for different message types (general messages, motion commands, emotion commands)

## Development

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Test:
   ```bash
   python -m pytest tests/test_ticos_client.py -v
   ```
   
For more examples, check out the [examples/python](../../examples/python) directory.
