import socket
import json
import threading
import logging
import time
from typing import Callable, Dict, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicosClient:
    def __init__(self, port=9999):
        self.port = port
        self.server_socket = None
        self.running = True
        self.handler = None
        self.motion_handler = None
        self.emotion_handler = None
        self._lock = threading.Lock()
        self.client_sockets: Set[socket.socket] = set()
        self.client_threads: Dict[socket.socket, threading.Thread] = {}

    def set_message_handler(self, handler: Callable[[object], None]):
        """Set custom message handler"""
        self.handler = handler

    def set_motion_handler(self, handler: Callable[[dict], None]):
        """Set handler function for motion messages
        
        Args:
            handler: Function that takes a parameters dictionary as argument
        """
        self.motion_handler = handler

    def set_emotion_handler(self, handler: Callable[[dict], None]):
        """Set handler function for emotion messages
        
        Args:
            handler: Function that takes a parameters dictionary as argument
        """
        self.emotion_handler = handler

    def start(self):
        """Start the server and listen for connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            logger.info(f"Server started, listening on port {self.port}")
            
            # Start accept thread
            threading.Thread(target=self._accept_connections, daemon=True).start()
            return True
        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}")
            self._cleanup()
            return False

    def stop(self):
        """Stop the server and close all connections"""
        self.running = False
        self._cleanup()
        logger.info("Server stopped")

    def _cleanup(self):
        """Clean up all connections"""
        with self._lock:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
                self.server_socket = None
            
            # Close all client connections
            for client_socket in self.client_sockets.copy():
                try:
                    client_socket.close()
                except:
                    pass
            self.client_sockets.clear()
            self.client_threads.clear()

    def _accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"New connection from {address}")
                
                with self._lock:
                    self.client_sockets.add(client_socket)
                    # Start client thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket,),
                        daemon=True
                    )
                    self.client_threads[client_socket] = client_thread
                    client_thread.start()
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {str(e)}")
                break

    def _handle_client(self, client_socket: socket.socket):
        """Handle messages from a client"""
        while self.running:
            try:
                # First read message length (4 bytes)
                length_bytes = self._receive_exactly(client_socket, 4)
                if not length_bytes:
                    break
                
                message_length = int.from_bytes(length_bytes, byteorder='big')
                
                # Then read the actual message
                message_bytes = self._receive_exactly(client_socket, message_length)
                if not message_bytes:
                    break
                
                message = json.loads(message_bytes.decode('utf-8'))
                
                if self.handler:
                    self.handler(message)

                if message.get('name') == 'motion':
                    if self.motion_handler:
                        self.motion_handler(message.get('arguments', {}))
                elif message.get('name') == 'emotion':
                    if self.emotion_handler:
                        self.emotion_handler(message.get('arguments', {}))
                else:
                    logger.info(f"Received message: {message}")
                    
            except Exception as e:
                logger.error(f"Error handling client message: {str(e)}")
                break
        
        # Clean up client connection
        with self._lock:
            try:
                client_socket.close()
            except:
                pass
            self.client_sockets.discard(client_socket)
            self.client_threads.pop(client_socket, None)
        logger.info("Client disconnected")

    def _receive_exactly(self, sock: socket.socket, n: int) -> bytes:
        """Helper method to receive exactly n bytes from a socket"""
        data = bytearray()
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except Exception:
                return None
        return data

    def send_message(self, message: dict) -> bool:
        """Send a message to all connected clients.

        Args:
            message: The message to send as a dictionary with 'name' and 'parameters' fields.
                Example: {'name': 'motion', 'parameters': {'id': '1', 'speed': 1.0}}

        Returns:
            bool: True if message was sent to at least one client successfully.
        """
        if not self.client_sockets:
            logger.warning("No clients connected")
            return False

        message_str = json.dumps(message)
        message_bytes = message_str.encode('utf-8')
        length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
        full_message = length_bytes + message_bytes

        success = False
        with self._lock:
            # Make a copy of the set to avoid modification during iteration
            for client_socket in self.client_sockets.copy():
                try:
                    client_socket.send(full_message)
                    success = True
                except Exception as e:
                    logger.warning(f"Failed to send message to a client: {str(e)}")
                    try:
                        client_socket.close()
                    except:
                        pass
                    self.client_sockets.discard(client_socket)
                    self.client_threads.pop(client_socket, None)

        return success

    def is_running(self):
        """Check if the server is running"""
        return self.running and bool(self.server_socket)

class DefaultMessageHandler:
    """Default implementation of message handler"""
    
    def handle_message(self, message):
        pass
