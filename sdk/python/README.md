# Ticos Client Python SDK

A Python SDK for the Ticos Agent system. This SDK allows you to create applications that can receive messages, handle motion and emotion commands, and store messages and memories locally.

## Features

- Local message and memory storage using SQLite
- Asynchronous message handling with thread-safe operations
- Type hints for better development experience
- Extensible architecture with support for custom handlers
- Built-in support for conversation handling and function calls
- Memory generation and management
- Support for different storage modes (INTERNAL, EXTERNAL)

## Installation

```bash
pip install ticos-client==0.5.0
```

Depends on ticos-agent 0.10.0 and above.

## Configuration

The SDK uses two configuration files:

1. `config.toml` - Main configuration file (TOML format)
   - Location: `~/.config/ticos/config.toml`
   - Contains device related settings and defaults

2. `session_config` - Session-specific agent configuration (JSON format)
   - Location (INTERNAL mode): `~/.config/ticos/session_config`
   - Location (EXTERNAL mode): `/path/to/tf_card/.config/ticos/session_config`
   - Contains session-specific settings and state

## Quick Start

### Basic Usage

```python
import logging
import time
from datetime import datetime
from ticos_client import TicosClient, SaveMode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def message_handler(message):
    """Handle incoming messages"""
    logger.info(f"Received message: {message}")

def motion_handler(parameters):
    """Handle motion commands"""
    logger.info(f"Motion command: {parameters}")

def emotion_handler(parameters):
    """Handle emotion commands"""
    logger.info(f"Emotion command: {parameters}")

def function_call_handler(name, parameters):
    """Handle function calls"""
    logger.info(f"Function call '{name}': {parameters}")

def conversation_handler(message_id, role, content):
    """Handle conversation events"""
    logger.info(f"Conversation - ID: {message_id}, Role: {role}, Content: {content}")

def main():
    # Create and configure client
    # Available save modes: SaveMode.INTERNAL, SaveMode.EXTERNAL
    client = TicosClient(port=9999, save_mode=SaveMode.INTERNAL)
    
    # Enable local storage (SQLite by default)
    client.enable_local_storage()
    
    # Set up handlers
    client.set_message_handler(message_handler)
    client.set_motion_handler(motion_handler)
    client.set_emotion_handler(emotion_handler)
    client.set_function_call_handler(function_call_handler)
    client.set_conversation_handler(conversation_handler)
    
    # Start the client
    if not client.start():
        logger.error("Failed to start client")
        return
    
    try:
        logger.info("Client started. Press Ctrl+C to stop.")
        
        # Keep the client running
        while True:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Client running at {current_time}")
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("Stopping client...")
    finally:
        client.stop()

if __name__ == "__main__":
    main()
```

## API Reference

### TicosClient

#### Constructor

```python
client = TicosClient(
    port: int = 9999,
    save_mode: SaveMode = SaveMode.INTERNAL,
    tf_root_dir: Optional[str] = None
)
```

Creates a new Ticos client instance.

**Parameters:**
- `port`: Port number to run the server on (default: 9999)
- `save_mode`: Storage mode (SaveMode.INTERNAL or SaveMode.EXTERNAL). SaveMode.INTERNAL will save the messages under the user's home directory. SaveMode.EXTERNAL will save the messages under the TF card root directory.
- `tf_root_dir`: Root directory for external storage (ignored if save_mode is EXTERNAL). If not provided, will use the root path of the TF card on the device in linux environment.

#### Methods

- `enable_local_storage(storage: Optional[StorageService] = None) -> None`
  - Enable local storage with an optional custom storage service
  - If no storage service is provided, a default SQLiteStorageService will be used
  - If don't need to save messages locally, can ignore this method.

- `start() -> bool`
  - Start the HTTP and WebSocket server
  - Returns True if startup was successful

- `stop() -> None`
  - Stop the server and clean up resources

- `is_running() -> bool`
  - Check if the server is running
  - Returns True if the server is running

- `set_message_handler(handler: Callable[[dict], None]) -> None`
  - Set handler for general messages
  - `handler`: Function that takes a message dictionary as parameter

- `set_motion_handler(handler: Callable[[dict], None]) -> None`
  - Set handler for motion commands
  - `handler`: Function that takes a parameters dictionary as parameter

- `set_emotion_handler(handler: Callable[[dict], None]) -> None`
  - Set handler for emotion commands
  - `handler`: Function that takes a parameters dictionary as parameter

- `set_function_call_handler(handler: Callable[[str, dict], None]) -> None`
  - Set handler for function calls
  - `handler`: Function that takes function name and parameters as parameters

- `set_conversation_handler(handler: Callable[[str, str, str], None]) -> None`
  - Set handler for conversation events
  - `handler`: Function that takes message_id, role, and content as parameters

## Message Formats

### Standard Message Format

### Message Types

#### 1. Motion Message

Triggers a physical motion or animation.

```json
{
    "name": "motion",
    "arguments": {
        "motion_tag": "string",    // The motion ID (required)
        "speed": 1.0,
        "repeat": 1,
        "wait": true
    }
}
```

#### 2. Emotion Message

Triggers an emotional expression or state change.

```json
{
    "name": "emotion",
    "arguments": {
        "emotion_tag": "string",   // The emotion ID (required)
        "intensity": 1.0,
        "duration": 2.5,
        "fade_in": 0.5
    }
}
```

#### 3. Conversation Message

Represents a chat message in a conversation.
message_id, role, content
```json
{
    "message_id": "msg_abc",   // The message ID
    "role": "user",            // "user" or "assistant"
    "content": "Hello!"        // The message content
}
```

#### 4. Function Call Message

Represents a function call to be executed.

```json
{
    "name": "function_name",    // Name of the function to call
    "parameters": {           // Parameters for the function
        "para_name1": "para_value1",
        "para_name2": "para_value2",
        ...
    }
}
```

#### 5. Raw Message

The raw message received from the Ticos Agent, it will be passed to the `set_message_handler` callback, which is generally defined in realtime protocol.

```json
{
  "content_index": 0,
  "event_id": "evt_NwZGB9s8xjxdoKDqSKmquw",
  "item_id": "resp_item_QhyuAfFaLaSkc3aJrCUsDa",
  "output_index": 0,
  "part": {
    "audio": null,
    "transcript": "",
    "type": "audio"
  },
  "response_id": "evt_khr4a6SUJ6ugVPBp9iiBna",
  "type": "response.content_part.done"
}
```
For details about the messages (events) in the realtime protocol, please refer to [Realtime Server Events](https://platform.openai.com/docs/api-reference/realtime-server-events).

## Advanced Features

### Storage Modes

The SDK supports different storage modes for flexibility:

1. **INTERNAL** (Default):
   - Uses SQLite for local storage
   - Simple to set up and use
   - Good for single-instance applications

2. **EXTERNAL**:
   - Uses an external storage service
   - Supports custom paths when `tf_root_dir` is specified

### Data Structure

The storage system maintains two main types of data:

1. **Messages**:
  Chat history.

2. **Memories**:
  The generated long-term memory.

In INTERNAL mode, data is stored in an SQLite database located at `~/.config/ticos/ticos.db`. In EXTERNAL mode, the storage location depends on the `tf_root_dir` configuration.

### Error Handling

- All network operations include error handling and retry logic
- Callbacks include error parameters for custom error handling
- Logging is configurable via Python's standard logging module

### Thread Safety

- All public methods are thread-safe
- Internal locking mechanisms prevent race conditions
- Asynchronous operations use proper synchronization

### Performance Considerations

- Batch operations where possible
- Efficient memory usage with lazy loading

## Best Practices

1. **Error Handling**: Always implement error handlers for network operations
2. **Logging**: Use the built-in logging for debugging and monitoring
3. **Resource Management**: Use context managers or `try/finally` blocks to ensure proper cleanup
4. **Message Validation**: Validate all incoming and outgoing messages
5. **Concurrency**: Be mindful of thread safety when implementing custom handlers

## Development

### Prerequisites

- Python 3.8+
- pip 20.0.0+
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/tiwater/ticos-client.git
   cd ticos-client/sdk/python
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
   
   Or using Tsinghua mirror (for users in China):
   ```bash
   pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

### Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_ticos_client.py -v

# Run tests with coverage report
pytest --cov=ticos_client tests/
```

### Building

Build the package:

```bash
python -m build
```

### Code Style

The project uses `black` for code formatting and `flake8` for linting:

```bash
# Format code
black .


# Check for style issues
flake8
```

## Examples

Check out the [examples/python](../../examples/python) directory for complete working examples, including:

- Basic client setup and usage
- Custom message handlers

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue on our [GitHub repository](https://github.com/tiwater/ticos-client/issues) or contact our support team.
