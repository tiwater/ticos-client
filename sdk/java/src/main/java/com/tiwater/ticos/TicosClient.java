package com.tiwater.ticos;

import org.json.JSONObject;
import java.io.*;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.concurrent.locks.ReentrantLock;
import java.util.logging.Logger;
import java.util.logging.Level;

/**
 * TicosClient is a Java server SDK for handling Ticos Agent connections.
 * It provides functionality for accepting TCP connections, handling messages,
 * and broadcasting messages to all connected agents.
 * 
 * <p>The server supports multiple concurrent connections and thread-safe operations.
 * It uses a length-prefixed JSON message protocol for communication.</p>
 * 
 * @version 0.2.0
 * @since 1.0
 */
public class TicosClient {
    private static final String TAG = "TicosClient";
    private static final Logger LOGGER = Logger.getLogger(TAG);
    private final int port;
    private ServerSocket serverSocket;
    private volatile boolean running = true;
    private Thread acceptThread;
    private MessageHandler messageHandler;
    private MotionHandler motionHandler;
    private EmotionHandler emotionHandler;
    private final ReentrantLock lock = new ReentrantLock();
    private final Set<ClientHandler> clients = new CopyOnWriteArraySet<>();

    /**
     * Interface for handling generic JSON messages received from clients.
     */
    public interface MessageHandler {
        void handleMessage(JSONObject message);
    }

    /**
     * Interface for handling motion-specific messages.
     */
    public interface MotionHandler {
        void handleMotion(JSONObject parameters);
    }

    /**
     * Interface for handling emotion-specific messages.
     */
    public interface EmotionHandler {
        void handleEmotion(JSONObject parameters);
    }

    /**
     * Constructs a TicosClient server.
     * 
     * @param port The port number to listen on
     */
    public TicosClient(int port) {
        this.port = port;
    }

    /**
     * Sets the handler for generic JSON messages.
     */
    public void setMessageHandler(MessageHandler handler) {
        this.messageHandler = handler;
    }

    /**
     * Sets the handler for motion messages.
     */
    public void setMotionHandler(MotionHandler handler) {
        this.motionHandler = handler;
    }

    /**
     * Sets the handler for emotion messages.
     */
    public void setEmotionHandler(EmotionHandler handler) {
        this.emotionHandler = handler;
    }

    /**
     * Starts the server and begins listening for connections.
     * 
     * @return true if server started successfully, false otherwise
     */
    public boolean start() {
        try {
            serverSocket = new ServerSocket(port);
            LOGGER.info("Server started on port " + port);
            
            // Start accept thread
            acceptThread = new Thread(this::acceptLoop);
            acceptThread.setDaemon(true);
            acceptThread.start();
            
            return true;
        } catch (IOException e) {
            LOGGER.log(Level.SEVERE, "Failed to start server: " + e.getMessage());
            cleanup();
            return false;
        }
    }

    /**
     * Stops the server and closes all client connections.
     */
    public void stop() {
        running = false;
        cleanup();
        LOGGER.info("Server stopped");
    }

    private void cleanup() {
        lock.lock();
        try {
            if (serverSocket != null) {
                try {
                    serverSocket.close();
                } catch (IOException e) {
                    LOGGER.log(Level.WARNING, "Error closing server socket: " + e.getMessage());
                }
                serverSocket = null;
            }
            
            // Close all client connections
            for (ClientHandler client : clients) {
                client.close();
            }
            clients.clear();
        } finally {
            lock.unlock();
        }
    }

    private void acceptLoop() {
        while (running) {
            try {
                Socket clientSocket = serverSocket.accept();
                LOGGER.info("New client connected from " + clientSocket.getInetAddress());
                
                ClientHandler clientHandler = new ClientHandler(clientSocket);
                clients.add(clientHandler);
                clientHandler.start();
            } catch (IOException e) {
                if (running) {
                    LOGGER.log(Level.WARNING, "Error accepting client connection: " + e.getMessage());
                }
                break;
            }
        }
    }

    /**
     * Sends a message to all connected clients.
     * 
     * @param message The message to broadcast, should contain 'name' and 'parameters' fields
     * @return true if message was sent to at least one client successfully
     */
    public boolean sendMessage(JSONObject message) {
        if (clients.isEmpty()) {
            LOGGER.warning("No clients connected");
            return false;
        }

        byte[] messageBytes = message.toString().getBytes(StandardCharsets.UTF_8);
        byte[] lengthBytes = ByteBuffer.allocate(4).putInt(messageBytes.length).array();
        byte[] fullMessage = new byte[4 + messageBytes.length];
        System.arraycopy(lengthBytes, 0, fullMessage, 0, 4);
        System.arraycopy(messageBytes, 0, fullMessage, 4, messageBytes.length);

        boolean success = false;
        for (ClientHandler client : clients) {
            if (client.sendMessage(fullMessage)) {
                success = true;
            }
        }
        return success;
    }

    /**
     * Handles communication with a single client.
     */
    private class ClientHandler {
        private final Socket socket;
        private final DataInputStream inputStream;
        private final DataOutputStream outputStream;
        private final Thread receiveThread;
        private volatile boolean running = true;

        public ClientHandler(Socket socket) throws IOException {
            this.socket = socket;
            this.inputStream = new DataInputStream(socket.getInputStream());
            this.outputStream = new DataOutputStream(socket.getOutputStream());
            this.receiveThread = new Thread(this::receiveLoop);
            this.receiveThread.setDaemon(true);
        }

        public void start() {
            receiveThread.start();
        }

        public void close() {
            running = false;
            try {
                socket.close();
            } catch (IOException e) {
                LOGGER.log(Level.WARNING, "Error closing client socket: " + e.getMessage());
            }
        }

        public boolean sendMessage(byte[] message) {
            try {
                synchronized (outputStream) {
                    outputStream.write(message);
                    outputStream.flush();
                }
                return true;
            } catch (IOException e) {
                LOGGER.warning("Failed to send message to client: " + e.getMessage());
                cleanup();
                return false;
            }
        }

        private void cleanup() {
            close();
            clients.remove(this);
        }

        private void receiveLoop() {
            while (running) {
                try {
                    // Read message length (4 bytes)
                    byte[] lengthBytes = receiveExactly(4);
                    if (lengthBytes == null) {
                        break;
                    }
                    int messageLength = ByteBuffer.wrap(lengthBytes).getInt();

                    // Read message content
                    byte[] messageBytes = receiveExactly(messageLength);
                    if (messageBytes == null) {
                        break;
                    }

                    String messageStr = new String(messageBytes, StandardCharsets.UTF_8);
                    JSONObject message = new JSONObject(messageStr);
                    
                    if (messageHandler != null) {
                        messageHandler.handleMessage(message);
                    }

                    String name = message.getString("name");
                    JSONObject parameters = message.optJSONObject("parameters");
                    if (parameters == null) {
                        parameters = new JSONObject();
                    }

                    if ("motion".equals(name)) {
                        if (motionHandler != null) {
                            motionHandler.handleMotion(parameters);
                        }
                    } else if ("emotion".equals(name)) {
                        if (emotionHandler != null) {
                            emotionHandler.handleEmotion(parameters);
                        }
                    } else {
                        LOGGER.info("Received message: " + messageStr);
                    }
                } catch (Exception e) {
                    if (running) {
                        LOGGER.warning("Error receiving message: " + e.getMessage());
                    }
                    break;
                }
            }

            cleanup();
            LOGGER.info("Client disconnected");
        }

        private byte[] receiveExactly(int n) {
            byte[] data = new byte[n];
            int totalRead = 0;
            while (totalRead < n) {
                try {
                    int read = inputStream.read(data, totalRead, n - totalRead);
                    if (read == -1) {
                        return null;
                    }
                    totalRead += read;
                } catch (IOException e) {
                    return null;
                }
            }
            return data;
        }
    }
}
