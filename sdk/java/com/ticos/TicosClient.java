package com.ticos;

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
    private MessageHandler handler;
    private final int reconnectInterval;
    private final ReentrantLock lock = new ReentrantLock();
    private byte[] lengthBuffer = new byte[4]; // Added: Initialize lengthBuffer

    public interface MessageHandler {
        void handleMessage(String func, String id);
    }

    public TicosClient(String host, int port) {
        this(host, port, 5000);
    }

    public TicosClient(String host, int port, int reconnectInterval) {
        this.host = host;
        this.port = port;
        this.reconnectInterval = reconnectInterval;
    }

    public void setHandler(MessageHandler handler) {
        this.handler = handler;
    }

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

        // Start reconnect thread outside the lock if needed
        if (needReconnect) {
            startReconnectThread();
        }

        return success;
    }

    private boolean checkConnection() {
        if (socket == null || !socket.isConnected() || socket.isClosed()) {
            return false;
        }
        try {
            return socket.getInputStream().available() >= 0;
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

    private void closeConnection() {
        lock.lock();
        try {
            closeConnectionNoLock();
        } finally {
            lock.unlock();
        }
    }

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

    public void disconnect() {
        running = false;  
        isReconnecting = false;
        if (reconnectThread != null) {
            reconnectThread.interrupt();
            try {
                reconnectThread.join(1000); // Wait up to 1 second for thread to finish
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
                                receiveThread.start();

                                LOGGER.info("Connected to server at " + host + ":" + port);
                                isReconnecting = false;
                                break;
                            } catch (IOException e) {
                                LOGGER.log(Level.WARNING, "Reconnection attempt " + retryCount + " failed: " + e.getMessage());
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
            reconnectThread.start();
            LOGGER.info("Started reconnection thread");
        } finally {
            lock.unlock();
        }
    }

    public boolean sendMessage(String func, String id) {
        lock.lock();
        try {
            if (socket == null || !checkConnection()) {
                LOGGER.log(Level.WARNING, "Not connected to server");
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
                LOGGER.log(Level.WARNING, "Failed to send message: " + e.getMessage());
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

    private void receiveLoop() {
        while (running) {
            try {
                if (!checkConnection()) {
                    break;
                }

                // Read message length (4 bytes)
                byte[] lengthBytes = new byte[4];
                if (!receiveExactly(lengthBytes)) {
                    break;
                }
                int messageLength = ByteBuffer.wrap(lengthBytes).getInt();

                // Read message content
                byte[] messageBytes = new byte[messageLength];
                if (!receiveExactly(messageBytes)) {
                    break;
                }

                String messageStr = new String(messageBytes, StandardCharsets.UTF_8);
                JSONObject message = new JSONObject(messageStr);
                
                if (handler != null) {
                    handler.handleMessage(message.getString("func"), message.getString("id"));
                } else {
                    LOGGER.info("Received message: " + messageStr);
                }
            } catch (Exception e) {
                LOGGER.log(Level.WARNING, "Error receiving message: " + e.getMessage());
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

    private boolean receiveExactly(byte[] buffer) {
        try {
            int totalRead = 0;
            while (totalRead < buffer.length) {
                int read = inputStream.read(buffer, totalRead, buffer.length - totalRead);
                if (read == -1) {
                    return false;
                }
                totalRead += read;
            }
            return true;
        } catch (IOException e) {
            return false;
        }
    }
}
