# Ticos Client Python SDK

A Python SDK for communicating with Ticos Server.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags?q=python-*)

## Installation

```bash
pip install ticos-client==0.1.5
```

## Usage

```python
from ticos import TicosClient

def main():
    # Create a client instance
    client = TicosClient("localhost", 9999)
    
    # Set message handlers
    client.set_motion_handler(lambda id: print(f"Received motion message id: {id}"))
    client.set_emotion_handler(lambda id: print(f"Received emotion message id: {id}"))
    client.set_message_handler(lambda msg: print(f"Received message: {msg}"))

    # Connect to server with auto-reconnect enabled
    if client.connect(True):
        print("Connected to server successfully")
        
        # Send a message with custom data
        message = {
            "func": "motion",
            "id": "1",
            "data": {
                "speed": 1.0,
                "repeat": 3
            }
        }
        
        if client.send_message(message):
            print("Message sent successfully")
        else:
            print("Failed to send message")

if __name__ == "__main__":
    main()
```

## API Reference

### TicosClient

#### Constructor

```python
client = TicosClient(host: str, port: int)
```

#### Methods

- `connect(auto_reconnect: bool = True) -> bool`
  - Connect to the server
  - Returns True if connection successful

- `disconnect()`
  - Disconnect from the server

- `send_message(message: dict) -> bool`
  - Send a message to the server
  - message: A dictionary containing the message data
  - Returns True if message sent successfully

- `set_message_handler(handler: Callable[[dict], None])`
  - Set handler for general messages

- `set_motion_handler(handler: Callable[[str], None])`
  - Set handler for motion messages

- `set_emotion_handler(handler: Callable[[str], None])`
  - Set handler for emotion messages

### Message Format

Messages should be dictionaries with the following structure:

```python
{
    "func": str,      # Function/message type (e.g., "motion", "emotion")
    "id": str,        # Message identifier
    "data": dict      # Optional additional data, TBD
}
```

## Development

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Run tests:
   ```bash
   python -m pytest tests/
   ```

## License

Apache License 2.0
