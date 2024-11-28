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
    client = TicosClient(host="localhost", port=9999)
    
    # Set message handler
    client.set_message_handler(handle_message)
    client.set_motion_handler(handle_motion_message)
    client.set_emotion_handler(handle_emotion_message)
    
    # Connect to server with auto-reconnect enabled
    if client.connect(auto_reconnect=True):
        print("Connected to server successfully")
        
        # Send a test message
        if client.send_message(func="test", id="123"):
            print("Message sent successfully")
        else:
            print("Failed to send message")
        
        # Keep the main thread running for a while to receive messages
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            pass
        
        # Disconnect when done
        client.disconnect()
    else:
        print("Failed to connect to server")

if __name__ == "__main__":
    main()
