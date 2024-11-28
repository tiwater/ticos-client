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
from ticos import TicosClient

def main():
    # Create a client instance
    client = TicosClient("localhost", 9999)
    
    # Set message handlers based on your needs
    client.set_motion_handler(lambda id: print(f"Received motion message id: {id}"))
    client.set_emotion_handler(lambda id: print(f"Received emotion message id: {id}"))
    client.set_message_handler(lambda msg: print(f"Received message: {msg}"))

    # Connect to server with auto-reconnect enabled
    if client.connect(True):
        print("Connected to server successfully")
        
        # Send a test message
        if client.send_message("test", "123"):
            print("Message sent successfully")
        else:
            print("Failed to send message")
        
        # Keep the main thread running to receive messages
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            client.disconnect()
    else:
        print("Failed to connect to server")

if __name__ == "__main__":
    main()
```


## Features Demonstrated

- Connecting to Ticos server
- Setting up message handlers
- Sending messages
- Auto-reconnection
- Proper connection cleanup

## Notes

- The example connects to a local server on port 9999 by default
- Use Ctrl+C to gracefully stop the example
- The client will automatically attempt to reconnect if the connection is lost
