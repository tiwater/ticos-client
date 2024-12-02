# Ticos Client Python SDK

A Python SDK for communicating with Ticos Server. This client SDK allows you to create applications that can send messages, handle motion and emotion commands, and maintain a heartbeat connection with the server.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags?q=python-*)

## Installation

```bash
pip install ticos-client==0.1.6
```

## Usage

```python
from ticos_client import TicosClient
import time

def message_handler(message):
    print(f"Received message: {message}")

def motion_handler(motion_id):
    print(f"Received motion command: {motion_id}")

def emotion_handler(emotion_id):
    print(f"Received emotion command: {emotion_id}")

def main():
    # Create and start the client
    client = TicosClient(port=9999)
    
    # Set message handlers
    client.set_message_handler(message_handler)
    client.set_motion_handler(motion_handler)
    client.set_emotion_handler(emotion_handler)
    
    # Start the client
    if not client.start():
        print("Failed to start client")
        return
    
    try:
        # Example: Send a heartbeat message
        client.send_message({
            "type": "heartbeat",
            "timestamp": time.time()
        })
        
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping client...")
    finally:
        client.stop()

if __name__ == "__main__":
    main()
```

## API Reference

### TicosClient

#### Constructor

```python
client = TicosClient(port: int)
```

Creates a new Ticos client instance.

#### Methods

- `start() -> bool`
  - Start the client
  - Returns True if startup successful

- `stop()`
  - Stop the client and clean up resources

- `send_message(message: dict) -> bool`
  - Send a message to the server
  - message: A dictionary containing the message data
  - Returns True if message sent successfully

- `set_message_handler(handler: Callable[[dict], None])`
  - Set handler for general messages
  - handler: Function that takes a message dictionary as parameter

- `set_motion_handler(handler: Callable[[str], None])`
  - Set handler for motion commands
  - handler: Function that takes a motion ID string as parameter

- `set_emotion_handler(handler: Callable[[str], None])`
  - Set handler for emotion commands
  - handler: Function that takes an emotion ID string as parameter

### Message Format

Messages should be dictionaries with the following structure:

```python
{
    "type": str,      # Message type (e.g., "heartbeat", "motion", "emotion")
    "timestamp": float,  # Optional timestamp
    "data": dict      # Optional additional data
}
```

## Features

- Simple and intuitive API for sending and receiving messages
- Automatic handling of connection management
- Thread-safe operations
- Support for different message types (general messages, motion commands, emotion commands)
- Built-in heartbeat mechanism

## Development

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

For more examples, check out the [examples/python](../../examples/python) directory.
