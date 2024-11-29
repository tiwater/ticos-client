from ticos_client import TicosClient
import time

def handle_message(message: object):
    print(f"Received message: {message}")

def handle_motion_message(id: str):
    print(f"Received motion message id: {id}")

def handle_emotion_message(id: str):
    print(f"Received emotion message id: {id}")


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
