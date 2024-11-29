import socket
import json
import threading
import logging
import time
from typing import Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicosClient:
    def __init__(self, host='localhost', port=9999, reconnect_interval=5):
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
        self.handler = None
        self.reconnect_interval = reconnect_interval
        self.reconnect_thread = None
        self.is_reconnecting = False
        self.motion_handler = None
        self.emotion_handler = None
        self._lock = threading.Lock()

    def set_message_handler(self, handler: Callable[[object], None]):
        """Set custom message handler"""
        self.handler = handler

    def set_motion_handler(self, handler: Callable[[str, str], None]):
        """Set handler function for motion messages"""
        self.motion_handler = handler

    def set_emotion_handler(self, handler: Callable[[str, str], None]):
        """Set handler function for emotion messages"""
        self.emotion_handler = handler

    def connect(self, auto_reconnect=True):
        """Connect to the motion service server"""
        if self.socket and self._check_connection():
            return True

        success = False
        need_reconnect = False
        with self._lock:
            try:
                self._cleanup_connection_no_lock()
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                # Start receiver thread
                threading.Thread(target=self._receive_loop, daemon=True).start()
                logger.info(f"Connected to server at {self.host}:{self.port}")
                success = True
            except Exception as e:
                logger.error(f"Connection failed: {str(e)}")
                self._cleanup_connection_no_lock()
                need_reconnect = auto_reconnect and not self.is_reconnecting

        # Start reconnect thread outside the lock if needed
        if need_reconnect:
            self._start_reconnect_thread()
        
        return success

    def disconnect(self):
        """Disconnect from the server"""
        self.running = False
        self.is_reconnecting = False
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=1.0)
        with self._lock:
            self._cleanup_connection_no_lock()
        logger.info("Disconnected from server")

    def _cleanup_connection(self):
        """Clean up the socket connection with lock"""
        with self._lock:
            self._cleanup_connection_no_lock()

    def _cleanup_connection_no_lock(self):
        """Clean up the socket connection without lock"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def _check_connection(self):
        """Check if the connection is still alive"""
        if not self.socket:
            return False
        try:
            # Check if the socket is still connected
            self.socket.send(b'')  # Send a no-op byte
            return True
        except socket.error:
            with self._lock:
                self._cleanup_connection_no_lock()
            return False

    def send_message(self, message: dict) -> bool:
        """Send a message to the server.

        Args:
            message: The message to send as a dictionary.

        Returns:
            bool: True if message was sent successfully, False otherwise.
        """
        if not self.is_connected():
            logger.warning("Not connected to server")
            return False

        try:
            message_str = json.dumps(message)
            message_bytes = message_str.encode('utf-8')
            length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
            
            self.socket.send(length_bytes + message_bytes)
            return True
        except Exception as e:
            logger.warning(f"Error sending message: {str(e)}")
            return False

    def _start_reconnect_thread(self):
        """Start reconnection thread"""
        with self._lock:
            if self.reconnect_thread and self.reconnect_thread.is_alive():
                return

            self.is_reconnecting = True
            self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
            self.reconnect_thread.start()

    def _reconnect_loop(self):
        """Reconnection loop"""
        retry_count = 0
        while self.running and self.is_reconnecting:
            retry_count += 1
            logger.info(f"Attempting to reconnect (attempt {retry_count}) in {self.reconnect_interval} seconds...")
            time.sleep(self.reconnect_interval)
            
            if not self.running:
                break
                
            try:
                with self._lock:
                    self._cleanup_connection_no_lock()
                    try:
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket.connect((self.host, self.port))
                        # Start receiver thread
                        threading.Thread(target=self._receive_loop, daemon=True).start()
                        logger.info(f"Connected to server at {self.host}:{self.port}")
                        self.is_reconnecting = False
                        break
                    except Exception as e:
                        logger.error(f"Reconnection attempt {retry_count} failed: {str(e)}")
                        self._cleanup_connection_no_lock()
                        continue
            except Exception as e:
                logger.error(f"Reconnection attempt {retry_count} failed: {str(e)}")
                continue
        
        if not self.running:
            logger.info("Reconnection stopped: client is shutting down")
        elif not self.is_reconnecting:
            logger.info("Reconnection stopped: connection established")

    def _receive_loop(self):
        """Receive messages from server"""
        while self.running:
            try:
                if not self._check_connection():
                    break

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
                
                if self.handler:
                    self.handler(message)

                if message['func'] == 'motion':
                    if self.motion_handler:
                        self.motion_handler(message['id'])
                elif message['func'] == 'emotion':
                    if self.emotion_handler:
                        self.emotion_handler(message['id'])
                else:
                    logger.info(f"Received message: {message}")
                    
            except Exception as e:
                logger.error(f"Error receiving message: {str(e)}")
                break
        
        # If we're here, the connection was lost
        with self._lock:
            self._cleanup_connection_no_lock()
        if not self.is_reconnecting and self.running:
            self._start_reconnect_thread()

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

    def is_connected(self):
        return self.socket is not None and self._check_connection()

class DefaultMessageHandler:
    """Default implementation of message handler"""
    
    def handle_message(self, message):
        pass
