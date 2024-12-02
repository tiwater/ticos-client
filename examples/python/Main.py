import sys
import os
import time
import logging

from ticos_client import TicosClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def message_handler(message):
    logger.info(f"Received message: {message}")

def motion_handler(parameters):
    logger.info(f"Received motion command with parameters: {parameters}")

def emotion_handler(parameters):
    logger.info(f"Received emotion command with parameters: {parameters}")

def main():
    # Create and start the client
    client = TicosClient(port=9999)
    client.set_message_handler(message_handler)
    client.set_motion_handler(motion_handler)
    client.set_emotion_handler(emotion_handler)
    
    if not client.start():
        logger.error("Failed to start client")
        return
    
    try:
        # Keep the main thread running and send heartbeat
        while True:
            client.send_message({
                "name": "heartbeat",
                "arguments": {
                    "timestamp": time.time()
                }
            })
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Stopping client...")
    finally:
        client.stop()

if __name__ == "__main__":
    main()
