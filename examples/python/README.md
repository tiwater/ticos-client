# Ticos Client Python Example

This is an example project demonstrating how to use the Ticos Client Python SDK.

## Running the Example

1. Make sure you have Python 3.6 or later installed
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the example:
   ```bash
   python Main.py
   ```

## Usage

Here's a simple example of how to use the Ticos Client:

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
    client.set_message_handler(message_handler)
    client.set_motion_handler(motion_handler)
    client.set_emotion_handler(emotion_handler)
    
    if not client.start():
        print("Failed to start client")
        return
    
    try:
        # Keep the main thread running and send heartbeat
        while True:
            client.send_message({
                "type": "heartbeat",
                "timestamp": time.time()
            })
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping client...")
    finally:
        client.stop()

if __name__ == "__main__":
    main()
```

## Features Demonstrated

- Creating and starting a Ticos client
- Setting up message, motion, and emotion handlers
- Sending periodic heartbeat messages
- Proper client initialization and cleanup
- Graceful shutdown on interrupt

## Notes

- The example creates a client on port 9999
- Heartbeat messages are sent every 5 seconds
- Use Ctrl+C to gracefully stop the client
- The client includes proper error handling and cleanup
