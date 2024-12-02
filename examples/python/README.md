# Ticos Client Python Example

This example demonstrates how to use the Ticos Client Python SDK to communicate with a Ticos Server.

## Requirements

- Python 3.6 or later
- ticos-client 0.1.7

## Installation

1. Install the Ticos Client SDK:
```bash
pip install ticos-client==0.1.7
```

2. Clone this repository:
```bash
git clone https://github.com/tiwater/ticos-client.git
cd ticos-client/examples/python
```

## Usage

Run the example:
```bash
python Main.py
```

The example demonstrates:
- Setting up message handlers for different message types
- Sending heartbeat messages
- Handling motion and emotion commands with parameters
- Proper connection management and cleanup

### Message Format

Messages use the following JSON format:

```json
{
    "name": "string",    // The message name (e.g., "motion", "emotion", "heartbeat")
    "arguments": {      // Parameters specific to the message type
        // message-specific parameters
    }
}
```

#### Motion Message Example

```json
{
    "name": "motion",
    "arguments": {
        "motion_tag": "hug",
        "speed": 1.0,
        "repeat": 3
    }
}
```

#### Emotion Message Example

```json
{
    "name": "emotion",
    "arguments": {
        "emotion_tag": "smile",
        "intensity": 0.8,
        "duration": 2.5
    }
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
