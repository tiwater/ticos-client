import socket
import json
import threading
import random
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MotionServer:
    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.running = False

    def start(self):
        """Start the motion service server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"Server started on {self.host}:{self.port}")
            
            # Start random message generator thread
            threading.Thread(target=self._random_message_generator, daemon=True).start()
            
            # Accept client connections
            while self.running:
                client_socket, address = self.server_socket.accept()
                logger.info(f"New client connected from {address}")
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()
                self.clients.append(client_socket)
                
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
        finally:
            self.stop()

    def stop(self):
        """Stop the server"""
        self.running = False
        for client in self.clients:
            client.close()
        if self.server_socket:
            self.server_socket.close()
        logger.info("Server stopped")

    def _handle_client(self, client_socket):
        """Handle client connection"""
        while self.running:
            try:
                # Read message length (4 bytes)
                length_bytes = self._receive_exactly(client_socket, 4)
                if not length_bytes:
                    break
                
                message_length = int.from_bytes(length_bytes, byteorder='big')
                
                # Read the actual message
                message_bytes = self._receive_exactly(client_socket, message_length)
                if not message_bytes:
                    break
                
                message = json.loads(message_bytes.decode('utf-8'))
                logger.info(f"Received from client: {message}")
                
            except Exception as e:
                logger.error(f"Error handling client: {str(e)}")
                break
        
        if client_socket in self.clients:
            self.clients.remove(client_socket)
        client_socket.close()

    def _receive_exactly(self, sock, n):
        """Helper method to receive exactly n bytes"""
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    def _random_message_generator(self):
        """Generate and send random messages to all clients"""
        functions = ['motion', 'emotion']
        motion_ids = ['greet', 'nod', 'wave', 'bow']
        emotion_ids = ['happy', 'sad', 'angry', 'surprised']
        
        while self.running:
            time.sleep(random.uniform(1, 5))  # Random delay between messages
            
            func = random.choice(functions)
            id_list = motion_ids if func == 'motion' else emotion_ids
            message = {
                'func': func,
                'id': random.choice(id_list)
            }
            
            # Send to all connected clients
            msg_bytes = json.dumps(message).encode('utf-8')
            length_prefix = len(msg_bytes).to_bytes(4, byteorder='big')
            
            for client in self.clients[:]:  # Copy list to avoid modification during iteration
                try:
                    client.sendall(length_prefix + msg_bytes)
                except:
                    # Remove dead clients
                    if client in self.clients:
                        self.clients.remove(client)

def main():
    server = MotionServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.stop()

if __name__ == "__main__":
    main()
