# Ticos Client Python SDK

A Python SDK for communicating with Ticos Server. This client SDK allows you to create applications that can send messages, handle motion and emotion commands, and maintain a heartbeat connection with the server.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags?q=python-*)

## Installation

```bash
pip install ticos-client==0.1.8
```

## Usage

```python
from ticos_client import TicosClient
import time

def message_handler(message):
    print(f"Received message: {message}")

def motion_handler(parameters):
    print(f"Received motion command with parameters: {parameters}")

def emotion_handler(parameters):
    print(f"Received emotion command with parameters: {parameters}")

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
            "name": "heartbeat",
            "arguments": {
                "timestamp": time.time()
            }
        })

        # Example: Send a motion command
        client.send_message({
            "name": "motion",
            "arguments": {
                "motion_tag": "hug",
                "speed": 1.0,
                "repeat": 3
            }
        })

        # Example: Send an emotion command
        client.send_message({
            "name": "emotion",
            "arguments": {
                "emotion_tag": "smile",
                "intensity": 0.8,
                "duration": 2.5
            }
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

#### Motion Message Parameters

```python
{
    "name": str,         # The motion ID
    "arguments": dict   # Motion speed (optional, default: 1.0)
}
```

#### Emotion Message Parameters

```python
{
    "name": str,           # The emotion ID
    "arguments": dict    # Emotion intensity (optional, default: 1.0)
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
