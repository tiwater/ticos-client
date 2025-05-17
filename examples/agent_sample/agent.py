import json
import asyncio
import websockets
import logging
import random
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicosAgent:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.websocket = None
        self.running = True

    async def _connect(self):
        """Connect to the WebSocket server"""
        uri = f"ws://{self.host}:{self.port}/realtime"
        try:
            self.websocket = await websockets.connect(uri)
            logger.info(f"Connected to WebSocket server at {uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
            return False

    async def connect(self):
        """Connect to the server"""
        return await self._connect()

    async def _disconnect(self):
        """Disconnect from the WebSocket server"""
        self.running = False
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
        logger.info("Disconnected from WebSocket server")

    def disconnect(self):
        """Disconnect from the server"""
        if self.loop:
            try:
                self.loop.run_until_complete(self._disconnect())
            except Exception as e:
                logger.error(f"Error during disconnect: {str(e)}")

    async def _cleanup(self):
        """Clean up WebSocket connection"""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None

    async def _send_message(self, message):
        """Send a message to the WebSocket server"""
        if not self.websocket:
            logger.error("Not connected to WebSocket server")
            return False
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    async def send_message(self, message):
        """Send a message to the server"""
        if not self.websocket:
            logger.error("Not connected to WebSocket server")
            return False
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    async def _receive_loop(self):
        """Receive messages from the WebSocket server"""
        while self.running:
            try:
                message = await self.websocket.recv()
                message_data = json.loads(message)
                logger.info(f"Received message: {message_data}")
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving message: {str(e)}")
                break
        
        await self._cleanup()

    async def start_receive_loop(self):
        """Start the receive loop"""
        return asyncio.create_task(self._receive_loop())



async def main():
    # Create and connect the agent
    agent = TicosAgent(host='localhost', port=9999)
    if not await agent.connect():
        return

    # Start receive loop
    receive_task = await agent.start_receive_loop()

    action_list = ["move_forward", "move_backward", "move_leftward", "move_rightward", "turn_left", "turn_right", "wave_hand", "hug", "give_me_five", "raise_fist", "thumb_up", "come_on"]
    
    try:
        # Send some test messages
        while True:
            # Send a motion command
            await agent.send_message({
                "name": "motion",
                "arguments": {
                    "motion_tag": random.choice(action_list),
                    "speed": random.uniform(0.5, 2.0),
                    "repeat": random.randint(1, 5)
                }
            })
            await asyncio.sleep(2)
            
            # Send an emotion command
            await agent.send_message({
                "name": "emotion",
                "arguments": {
                    "emotion_tag": str(random.randint(1, 3)),
                    "intensity": random.uniform(0.1, 1.0),
                    "duration": random.uniform(1.0, 5.0)
                }
            })
            await asyncio.sleep(2)
    except KeyboardInterrupt:
        logger.info("Stopping agent...")
    finally:
        agent.running = False
        if agent.websocket:
            await agent.websocket.close()
        await receive_task

if __name__ == "__main__":
    asyncio.run(main())
