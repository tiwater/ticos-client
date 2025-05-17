import sys
import os
import time
import logging
import random
from datetime import datetime
from enum import Enum

from ticos_client import TicosClient, SaveMode, SQLiteStorageService

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
    client = TicosClient(port=9999, save_mode = SaveMode.INTERNAL)
    
    # client = TicosClient(port=9999, save_mode = SaveMode.EXTERNAL, tf_root_dir = '/Users/sawyer/.config/ticos/sim_sd')
    client.enable_local_storage()
    client.set_message_handler(message_handler)
    client.set_motion_handler(motion_handler)
    client.set_emotion_handler(emotion_handler)
    
    if not client.start():
        logger.error("Failed to start client")
        return
    
    try:
        # Keep the main thread running and do your own business
        while True:
            # Send test messages every 10 seconds
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Send a test message
            test_message = {
                "name": "test",
                "arguments": {
                    "timestamp": current_time,
                    "random_value": random.randint(1, 100)
                }
            }
            client.send_message(test_message)
            
            logger.info(f"Sent test messages at {current_time}")
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Stopping client...")
    finally:
        client.stop()

if __name__ == "__main__":
    main()
