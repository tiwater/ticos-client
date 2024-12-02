import sys
import os
import time
import logging

from ticos_client import TicosClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def message_handler(message):
    logger.info(f"Received message: {message}")

def motion_handler(motion_id):
    logger.info(f"Received motion command: {motion_id}")

def emotion_handler(emotion_id):
    logger.info(f"Received emotion command: {emotion_id}")

def main():
    # Create and start the server
    server = TicosClient(port=9999)
    server.set_message_handler(message_handler)
    server.set_motion_handler(motion_handler)
    server.set_emotion_handler(emotion_handler)
    
    if not server.start():
        logger.error("Failed to start server")
        return
    
    try:
        # Keep the main thread running
        while True:
            # Periodically broadcast a heartbeat message to all clients
            server.send_message({
                "type": "heartbeat",
                "timestamp": time.time()
            })
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Stopping server...")
    finally:
        server.stop()

if __name__ == "__main__":
    main()
