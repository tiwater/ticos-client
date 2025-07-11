import time
import logging
from datetime import datetime, timedelta
import sys
import os

# Import the appropriate key detection based on the operating system
if os.name == 'nt':  # Windows
    import msvcrt
else:  # Unix-like systems (Linux, macOS)
    import select
    import termios
    import tty

from ticos_client import TicosClient, SaveMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client: TicosClient = None
# Track the last time a dance message was sent
last_dance_message_time: datetime = datetime.min
# Minimum interval between dance messages (30 seconds)
DANCE_MESSAGE_INTERVAL = timedelta(seconds=30)

def message_handler(message):
    if not isinstance(message, dict) or message.get("type") != "response.video.done":
        logger.info(f"Received message: {message}")
    else:
        logger.debug(f"Received message: {message}")

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

def send_realtime_message():
    
    message = {
        "type": "response.create",
        "response": {
            "input": [{
                "role": "system",
                "content": [{
                    "type": "input_text",
                    "text": "你是一个人形机器人，刚才跳完了舞。请口语化的简短的说你跳完了舞并与客户互动。"
                }]
            }]
        }
    }
    
    global client
    try:
        client.send_realtime_message(message)
        logger.info(f"Sent realtime message for dance request. Message: {message}")
    except Exception as e:
        logger.error(f"Error in delayed send: {e}")

def is_key_pressed():
    """Check if a key is pressed. Returns the key if pressed, None otherwise."""
    if os.name == 'nt':  # Windows
        return msvcrt.kbhit()
    else:  # Unix-like systems
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def get_key():
    """Get the pressed key."""
    if os.name == 'nt':  # Windows
        key = msvcrt.getch()
        if key == b'\x1b':  # ESC
            return 'esc'
        return key.decode('utf-8', 'ignore').lower()
    else:  # Unix-like systems
        key = sys.stdin.read(1)
        if key == '\x1b':  # ESC
            # Check if there are more characters (for escape sequences)
            if select.select([sys.stdin], [], [], 0.1)[0]:
                _ = sys.stdin.read(2)  # Read the rest of the escape sequence
            return 'esc'
        return key.lower()

def main():
    global client
    # Set up terminal for non-blocking input on Unix-like systems
    if os.name != 'nt':
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(sys.stdin.fileno())
    
    # Create and start the client
    client = TicosClient(port=9999, save_mode=SaveMode.INTERNAL)
    # client = TicosClient(port=9999, save_mode=SaveMode.EXTERNAL)
    # client = TicosClient(port=9999, save_mode=SaveMode.EXTERNAL, tf_root_dir='/Users/sawyer/.config/ticos/sim_sd')
    client.set_message_handler(message_handler)
    
    # client.enable_local_storage(db_filename="scripts/role1.db")
    client.enable_local_storage()
    client.set_motion_handler(motion_handler)
    client.set_emotion_handler(emotion_handler)
    client.set_function_call_handler(function_call_handler)
    client.set_conversation_handler(conversation_handler)
    
    if not client.start():
        logger.error("Failed to start client")
        # Restore terminal settings on Unix-like systems
        if os.name != 'nt':
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return
    
    try:
        logger.info("Press 'Q' or 'Esc' to exit...")
        last_log_time = time.time()
        log_interval = 30  # seconds
        
        # Main loop
        while True:
            # Check for key press
            if is_key_pressed():
                key = get_key()
                if key == 'q' or key == 'esc':
                    logger.info("Exit key detected. Stopping client...")
                    break
                elif key == 'm':
                    send_realtime_message()
                elif key == 'p':
                    client.stop()
                elif key == 's':
                    client.start()
                elif key == 'c':
                    # Send cancel response message
                    try:
                        cancel_message = {
                            "type": "response.cancel"
                        }
                        client.send_realtime_message(cancel_message)
                        logger.info(f"Sent cancel message: {cancel_message}")
                    except Exception as e:
                        logger.error(f"Error sending cancel message: {e}")
            
            # Log status periodically
            current_time = time.time()
            if current_time - last_log_time >= log_interval:
                last_log_time = current_time
                logger.info(f"I'm still alive at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Small delay to prevent high CPU usage
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping client...")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Clean up
        client.stop()
        # Restore terminal settings on Unix-like systems
        if os.name != 'nt':
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    main()
