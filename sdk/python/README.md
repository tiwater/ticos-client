# Ticos Client Python SDK

A Python client SDK for communicating with Ticos Server.

## Installation

```bash
pip install ticos-client
```

## Usage

```python
from ticos_client import TicosClient

# Create a client instance
client = TicosClient(host="localhost", port=8080)

# Connect to server
client.connect(auto_reconnect=True)

# Define message handler
def handle_message(func, id):
    print(f"Received message - func: {func}, id: {id}")

# Set message handler
client.set_handler(handle_message)

# Send message
client.send_message(func="test", id="123")

# Disconnect when done
client.disconnect()
```

## Features

- Automatic reconnection
- Message handling
- Thread-safe communication
- Configurable connection settings

## Requirements

- Python 3.6 or higher

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
