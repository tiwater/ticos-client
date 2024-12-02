import socket
import json
import threading
import time
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicosAgent:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
        self.receive_thread = None

    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to server at {self.host}:{self.port}")
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
            self._cleanup()
            return False

    def disconnect(self):
        """Disconnect from the server"""
        self.running = False
        self._cleanup()
        logger.info("Disconnected from server")

    def _cleanup(self):
        """Clean up connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def send_message(self, message):
        """Send a message to the server"""
        if not self.socket:
            logger.error("Not connected to server")
            return False
        
        try:
            message_str = json.dumps(message)
            message_bytes = message_str.encode('utf-8')
            length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
            self.socket.send(length_bytes + message_bytes)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    def _receive_loop(self):
        """Receive messages from the server"""
        while self.running:
            try:
                # First read message length (4 bytes)
                length_bytes = self._receive_exactly(4)
                if not length_bytes:
                    break
                
                message_length = int.from_bytes(length_bytes, byteorder='big')
                
                # Then read the actual message
                message_bytes = self._receive_exactly(message_length)
                if not message_bytes:
                    break
                
                message = json.loads(message_bytes.decode('utf-8'))
                logger.info(f"Received message: {message}")
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving message: {str(e)}")
                break
        
        self._cleanup()

    def _receive_exactly(self, n):
        """Helper method to receive exactly n bytes"""
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.socket.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except Exception:
                return None
        return data

def main():
    # Create and connect the agent
    agent = TicosAgent(host='localhost', port=9999)
    if not agent.connect():
        return
    
    try:
        # Send some test messages
        while True:
            # Send a motion command
            agent.send_message({
                "name": "motion",
                "parameters": {
                    "id": str(random.randint(1, 3)),
                    "speed": random.uniform(0.5, 2.0),
                    "repeat": random.randint(1, 5)
                }
            })
            time.sleep(2)
            
            # Send an emotion command
            agent.send_message({
                "name": "emotion",
                "parameters": {
                    "id": str(random.randint(1, 3)),
                    "intensity": random.uniform(0.1, 1.0),
                    "duration": random.uniform(1.0, 5.0)
                }
            })
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopping agent...")
    finally:
        agent.disconnect()

if __name__ == "__main__":
    main()
