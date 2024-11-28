package com.tiwater.ticos;

import org.json.JSONObject;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.locks.ReentrantLock;
import java.util.logging.Logger;
import java.util.logging.Level;

/**
 * TicosClient is a Java client SDK for communicating with Ticos Server.
 * It provides functionality for establishing TCP connections, sending messages,
 * and handling different types of server responses through dedicated handlers.
 * 
 * <p>The client supports automatic reconnection and thread-safe operations.
 * It uses a length-prefixed JSON message protocol for communication.</p>
 * 
 * @version 0.1.0
 * @since 1.0
 */
public class TicosClient {
    private static final String TAG = "TicosClient";
    private static final Logger LOGGER = Logger.getLogger(TAG);
    private final String host;
    private final int port;
    private Socket socket;
    private DataInputStream inputStream;
    private DataOutputStream outputStream;
    private volatile boolean running = true;  
    private volatile boolean isReconnecting;
    private Thread receiveThread;
    private Thread reconnectThread;
    private MessageHandler messageHandler;
    private MotionHandler motionHandler;
    private EmotionHandler emotionHandler;
    private final int reconnectInterval;
    private final ReentrantLock lock = new ReentrantLock();

    /**
     * Interface for handling generic JSON messages received from the server.
     */
    public interface MessageHandler {
        /**
         * Called when a message is received from the server.
         * 
         * @param message The JSON message received from the server
         */
        void handleMessage(JSONObject message);
    }

    /**
     * Interface for handling motion-specific messages.
     */
    public interface MotionHandler {
        /**
         * Called when a motion message is received from the server.
         * 
         * @param id The ID of the motion message
         */
        void handleMotion(String id);
    }

    /**
     * Interface for handling emotion-specific messages.
     */
    public interface EmotionHandler {
        /**
         * Called when an emotion message is received from the server.
         * 
         * @param id The ID of the emotion message
         */
        void handleEmotion(String id);
    }

    /**
     * Constructs a TicosClient with default reconnection interval (5000ms).
     * 
     * @param host The server hostname or IP address
     * @param port The server port number
     */
    public TicosClient(String host, int port) {
        this(host, port, 5000);
    }

    /**
     * Constructs a TicosClient with custom reconnection interval.
     * 
     * @param host The server hostname or IP address
     * @param port The server port number
     * @param reconnectInterval The interval in milliseconds between reconnection attempts
     */
    public TicosClient(String host, int port, int reconnectInterval) {
        this.host = host;
        this.port = port;
        this.reconnectInterval = reconnectInterval;
    }

    /**
     * Sets the handler for generic JSON messages.
     * 
     * @param handler The message handler implementation
     */
    public void setMessageHandler(MessageHandler handler) {
        this.messageHandler = handler;
    }

    /**
     * Sets the handler for motion messages.
     * 
     * @param handler The motion handler implementation
     */
    public void setMotionHandler(MotionHandler handler) {
        this.motionHandler = handler;
    }

    /**
     * Sets the handler for emotion messages.
     * 
     * @param handler The emotion handler implementation
     */
    public void setEmotionHandler(EmotionHandler handler) {
        this.emotionHandler = handler;
    }

    /**
     * Establishes a connection to the server.
     * 
     * @param autoReconnect If true, automatically attempts to reconnect when connection is lost
     * @return true if connection was successful, false otherwise
     */
    public synchronized boolean connect(boolean autoReconnect) {
        if (socket != null && checkConnection()) {
            return true;
        }

        boolean success = false;
        boolean needReconnect = false;
        lock.lock();
        try {
            closeConnectionNoLock();

            try {
                socket = new Socket(host, port);
                inputStream = new DataInputStream(socket.getInputStream());
                outputStream = new DataOutputStream(socket.getOutputStream());
                
                // Start receiver thread
                receiveThread = new Thread(this::receiveLoop);
                receiveThread.setDaemon(true);
                receiveThread.start();

                LOGGER.info("Connected to server at " + host + ":" + port);
                success = true;
            } catch (IOException e) {
                LOGGER.log(Level.WARNING, "Connection failed: " + e.getMessage());
                closeConnectionNoLock();
                needReconnect = autoReconnect && !isReconnecting;
            }
        } finally {
            lock.unlock();
        }

        if (needReconnect) {
            startReconnectThread();
        }

        return success;
    }

    /**
     * Checks if the current connection is valid.
     * 
     * @return true if connection is valid, false otherwise
     */
    private boolean checkConnection() {
        if (socket == null || !socket.isConnected() || socket.isClosed()) {
            return false;
        }
        try {
            socket.getOutputStream().write(new byte[0]);
            return true;
        } catch (IOException e) {
            lock.lock();
            try {
                closeConnectionNoLock();
            } finally {
                lock.unlock();
            }
            return false;
        }
    }

    /**
     * Closes the current connection without acquiring the lock.
     * This method should only be called when the lock is already held.
     */
    private void closeConnectionNoLock() {
        try {
            if (inputStream != null) {
                inputStream.close();
            }
            if (outputStream != null) {
                outputStream.close();
            }
            if (socket != null) {
                socket.close();
            }
        } catch (IOException e) {
            LOGGER.log(Level.WARNING, "Error closing connection: " + e.getMessage());
        } finally {
            socket = null;
            inputStream = null;
            outputStream = null;
        }
    }

    /**
     * Disconnects from the server and stops all background threads.
     * This method is thread-safe and can be called at any time.
     */
    public void disconnect() {
        running = false;  
        isReconnecting = false;
        if (reconnectThread != null) {
            reconnectThread.interrupt();
            try {
                reconnectThread.join(1000);
            } catch (InterruptedException ignored) {
            }
            reconnectThread = null;
        }
        lock.lock();
        try {
            closeConnectionNoLock();
        } finally {
            lock.unlock();
        }
        LOGGER.info("Disconnected from server");
    }

    /**
     * Sends a message to the server.
     * 
     * @param func The function name or message type
     * @param id The message identifier
     * @return true if message was sent successfully, false otherwise
     */
    public boolean sendMessage(String func, String id) {
        lock.lock();
        try {
            if (socket == null || !checkConnection()) {
                LOGGER.warning("Not connected to server");
                if (!isReconnecting && running) {
                    startReconnectThread();
                }
                return false;
            }

            try {
                JSONObject message = new JSONObject();
                message.put("func", func);
                message.put("id", id);

                byte[] messageBytes = message.toString().getBytes(StandardCharsets.UTF_8);
                byte[] lengthBytes = ByteBuffer.allocate(4).putInt(messageBytes.length).array();

                outputStream.write(lengthBytes);
                outputStream.write(messageBytes);
                outputStream.flush();
                return true;
            } catch (Exception e) {
                LOGGER.warning("Failed to send message: " + e.getMessage());
                closeConnectionNoLock();
                if (!isReconnecting && running) {
                    startReconnectThread();
                }
                return false;
            }
        } finally {
            lock.unlock();
        }
    }

    /**
     * Background thread that handles receiving messages from the server.
     * This method runs continuously until the client is disconnected.
     */
    private void receiveLoop() {
        while (running) {
            try {
                if (!checkConnection()) {
                    break;
                }

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

                String func = message.getString("func");
                String id = message.getString("id");

                if ("motion".equals(func) && motionHandler != null) {
                    motionHandler.handleMotion(id);
                } else if ("emotion".equals(func) && emotionHandler != null) {
                    emotionHandler.handleEmotion(id);
                } else {
                    LOGGER.info("Received message: " + messageStr);
                }
            } catch (Exception e) {
                LOGGER.warning("Error receiving message: " + e.getMessage());
                break;
            }
        }

        // If we're here, the connection was lost
        lock.lock();
        try {
            closeConnectionNoLock();
            if (!isReconnecting && running) {
                startReconnectThread();
            }
        } finally {
            lock.unlock();
        }
    }

    /**
     * Reads exactly n bytes from the input stream.
     * 
     * @param n The number of bytes to read
     * @return The read bytes, or null if an error occurred
     */
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

    /**
     * Starts a background thread that attempts to reconnect to the server.
     * This method is thread-safe and can be called at any time.
     */
    private void startReconnectThread() {
        lock.lock();
        try {
            if (reconnectThread != null && reconnectThread.isAlive()) {
                return;
            }

            isReconnecting = true;
            reconnectThread = new Thread(() -> {
                int retryCount = 0;
                while (isReconnecting && running) {
                    try {
                        retryCount++;
                        LOGGER.info("Attempting to reconnect (attempt " + retryCount + ") in " + (reconnectInterval/1000) + " seconds...");
                        Thread.sleep(reconnectInterval);
                        if (!running) {
                            break;
                        }

                        lock.lock();
                        try {
                            closeConnectionNoLock();
                            try {
                                socket = new Socket(host, port);
                                inputStream = new DataInputStream(socket.getInputStream());
                                outputStream = new DataOutputStream(socket.getOutputStream());
                                
                                // Start receiver thread
                                receiveThread = new Thread(this::receiveLoop);
                                receiveThread.setDaemon(true);
                                receiveThread.start();

                                LOGGER.info("Connected to server at " + host + ":" + port);
                                isReconnecting = false;
                                break;
                            } catch (IOException e) {
                                LOGGER.warning("Reconnection attempt " + retryCount + " failed: " + e.getMessage());
                                closeConnectionNoLock();
                            }
                        } finally {
                            lock.unlock();
                        }
                    } catch (InterruptedException e) {
                        break;
                    }
                }
                
                if (!running) {
                    LOGGER.info("Reconnection stopped: client is shutting down");
                } else if (!isReconnecting) {
                    LOGGER.info("Reconnection stopped: connection established");
                }
            });
            reconnectThread.setDaemon(true);
            reconnectThread.start();
        } finally {
            lock.unlock();
        }
    }
}
