import time
import logging
from datetime import datetime

from ticos_client import TicosClient, SaveMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def message_handler(message):
    logger.info(f"Received message: {message}")

def motion_handler(parameters):
    logger.info(f"Received motion command with parameters: {parameters}")

def emotion_handler(parameters):
    logger.info(f"Received emotion command with parameters: {parameters}")

def function_call_handler(name, parameters):
    logger.info(f"Received function call '{name}' with parameters: {parameters}")

def conversation_handler(message_id, role, content):
    """
    Handle conversation events including user messages and assistant responses.
    
    Args:
        message_id: The unique ID of the message (item_id)
        role: The role of the message sender ('user' or 'assistant')
        content: The content of the message
    """
    logger.info(f"Conversation event - Message ID: {message_id}, Role: {role}, Content: {content}")

def main():
    # Create and start the client
    client = TicosClient(port=9999, save_mode = SaveMode.INTERNAL)
    # client = TicosClient(port=9999, save_mode = SaveMode.EXTERNAL)
    # client = TicosClient(port=9999, save_mode = SaveMode.EXTERNAL, tf_root_dir = '/Users/sawyer/.config/ticos/sim_sd')
    client.enable_local_storage()
    client.set_message_handler(message_handler)
    client.set_motion_handler(motion_handler)
    client.set_emotion_handler(emotion_handler)
    client.set_function_call_handler(function_call_handler)
    client.set_conversation_handler(conversation_handler)
    
    if not client.start():
        logger.error("Failed to start client")
        return
    
    try:
        # Keep the main thread running and do your own business
        while True:
            # Print log every 30 seconds
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info(f"I'm still alive at {current_time}")
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Stopping client...")
    finally:
        client.stop()

if __name__ == "__main__":
    main()
