# Ticos Client Python Example

This example demonstrates how to use the Ticos Client Python SDK to communicate with a Ticos Server. It showcases various features including message handling, motion/emotion commands, conversation handling, and function calls.

## Table of Contents

- [Ticos Client Python Example](#ticos-client-python-example)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
    - [Get Source](#get-source)
    - [Using pip to install the dependencies](#using-pip-to-install-the-dependencies)
  - [Usage](#usage)
    - [Basic Example](#basic-example)
    - [Message Types](#message-types)
      - [1. Motion Commands](#1-motion-commands)
      - [2. Emotion Commands](#2-emotion-commands)
      - [3. Conversation Handling](#3-conversation-handling)
      - [4. Function Calls](#4-function-calls)
    - [Storage Modes](#storage-modes)
  - [API Reference](#api-reference)
  - [License](#license)
  - [Support](#support)

## Features

- Support for both HTTP and WebSocket connections
- Local message and memory storage using SQLite
- Thread-safe operations with proper connection management
- Built-in support for various message types:
  - General messages
  - Motion commands
  - Emotion commands
  - Conversation handling
  - Function calls
  - Heartbeat monitoring
- Configurable storage modes (INTERNAL/EXTERNAL)
- Comprehensive error handling and logging

## Requirements

- Python 3.8 or later
- ticos-client 0.5.8 or later
- (Optional) For development: pytest, black, flake8

## Installation

### Get Source

   Clone the repository:
   ```bash
   git clone https://github.com/tiwater/ticos-client.git
   cd ticos-client/examples/python
   ```

### Using pip to install the dependencies

    ```bash
    # Or install a specific version
    pip install -r requirements.txt
    ```


## Usage

### Basic Example

Run the example:

```bash
python Main.py
```

This will start a client that:
- An executor that runs on port 9999
- Sets up handlers for different message types
- Periodically logs its status
- Properly cleans up resources on exit

### Message Types

The example demonstrates handling of various message types:

#### 1. Motion Commands

Trigger physical movements or animations:

```python
def motion_handler(parameters):
    logger.info(f"Motion command: {parameters}")
    # Example parameters:
    # {
    #     "motion_tag": "wave_hand",
    #     "speed": 1.0,
    #     "repeat": 2,
    #     "wait": True
    # }
```

#### 2. Emotion Commands

Control emotional expressions:

```python
def emotion_handler(parameters):
    logger.info(f"Emotion command: {parameters}")
    # Example parameters:
    # {
    #     "emotion_tag": "happy",
    #     "intensity": 0.8,
    #     "duration": 3.0,
    #     "fade_in": 0.5
    # }
```

#### 3. Conversation Handling

Process conversation events:

```python
def conversation_handler(message_id, role, content):
    logger.info(f"Conversation - ID: {message_id}, Role: {role}, Content: {content}")
    # Example values:
    # message_id: "msg_123"
    # role: "user" or "assistant"
    # content: "Hello, how are you?"
```

#### 4. Function Calls

Handle function invocations:

```python
def function_call_handler(name, parameters):
    logger.info(f"Function call '{name}': {parameters}")
    # Example:
    # name: "get_weather"
    # parameters: {"location": "Beijing", "unit": "celsius"}
```

### Storage Modes

The example supports different storage configurations:

1. **INTERNAL** (Default):
   ```python
   client = TicosClient(port=9999, save_mode=SaveMode.INTERNAL)
   client.enable_local_storage()
   ```

2. **EXTERNAL**:
   ```python
   client = TicosClient(
       port=9999,
       save_mode=SaveMode.EXTERNAL,
       tf_root_dir='/path/to/storage'
   )
   ```
   If tf_root_dir is not provided, will use the root path of the TF card on the device in linux environment.

## API Reference

For detailed API documentation, please refer to the [SDK Documentation](../../sdk/python/README.md).

## License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## Support

For support, please open an issue on our [GitHub repository](https://github.com/tiwater/ticos-client/issues).
