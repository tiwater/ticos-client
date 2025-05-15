package com.tiwater.ticos;

import com.tiwater.ticos.server.UnifiedServer;
import com.tiwater.ticos.storage.SQLiteStorageService;
import com.tiwater.ticos.storage.StorageService;
import com.tiwater.ticos.util.ConfigUtil;
import com.tiwater.ticos.util.HttpUtil;
import org.json.JSONObject;

import java.io.*;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.concurrent.locks.ReentrantLock;
import java.util.logging.Logger;
import java.util.logging.Level;
import java.util.UUID;

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
    private volatile boolean running = true;
    private Thread acceptThread;
    private MessageHandler messageHandler;
    private MotionHandler motionHandler;
    private EmotionHandler emotionHandler;
    private final ReentrantLock lock = new ReentrantLock();
    // Removed ClientHandler as it's not used in the current implementation
    private StorageService storageService;
    private UnifiedServer unifiedServer;
    private int messageCounter = 0;
    private final int memoryRounds;
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    /**
     * Enable local storage with the provided storage service implementation.
     * If not called, local storage functionality will be disabled.
     *
     * @param storageService The storage service implementation to use
     */
    public void enableLocalStorage(StorageService storageService) {
        this.storageService = storageService;
    }

    // Removed generateMemories as it's replaced by generateMemory

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
        this.memoryRounds = ConfigUtil.getMemoryRounds();
        
        // Initialize SQLite storage by default
        try {
            Class.forName("org.sqlite.JDBC");
            enableLocalStorage(new SQLiteStorageService());
        } catch (ClassNotFoundException e) {
            LOGGER.warning("SQLite JDBC driver not found. Local storage will be disabled.");
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Failed to initialize local storage: " + e.getMessage(), e);
        }
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
            // Create and start the unified server for both HTTP and WebSocket
            unifiedServer = new UnifiedServer(port, storageService, this);
            unifiedServer.start();
            LOGGER.info("Server started on port " + port);
            return true;
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Failed to start server: " + e.getMessage(), e);
            return false;
        }
    }

    /**
     * Stops the server and closes all client connections.
     */
    public void stop() {
        if (unifiedServer != null) {
            unifiedServer.stop();
            LOGGER.info("Server stopped");
        }
    }

    private void cleanup() {
        // Cleanup resources if needed
    }

    /**
     * Handle WebSocket messages from clients
     * This method is called by the UnifiedServer when a WebSocket message is received
     * 
     * @param message The JSON message received from the client
     * @param clientChannel The WebSocket channel that sent the message
     */
    public void handleWebSocketMessage(JSONObject message, Object clientChannel) {
        try {
            // Process the message
            String name = message.optString("name");
            JSONObject arguments = message.optJSONObject("arguments");
            
            if (arguments != null) {
                // Save the message if local storage is enabled
                if (storageService != null) {
                    JSONObject storageMessage = new JSONObject();
                    long timestamp = System.currentTimeMillis();
                    storageMessage.put("id", timestamp);
                    storageMessage.put("role", "assistant");
                    storageMessage.put("content", message.toString());
                    storageMessage.put("datetime", dateFormat.format(new Date(timestamp)));
                    storageService.saveMessage(storageMessage);
                    
                    // Check if we need to generate a memory
                    messageCounter++;
                    if (messageCounter >= memoryRounds) {
                        generateMemory();
                        messageCounter = 0;
                    }
                }
                
                // Handle different message types
                if ("message".equals(name) && messageHandler != null) {
                    messageHandler.handleMessage(arguments);
                } else if ("motion".equals(name) && motionHandler != null) {
                    motionHandler.handleMotion(arguments);
                } else if ("emotion".equals(name) && emotionHandler != null) {
                    emotionHandler.handleEmotion(arguments);
                }
            }
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error handling message: " + e.getMessage(), e);
        }
    }

    /**
     * Sends a message to all connected clients.
     * 
     * @param message The message to broadcast, should contain 'name' and 'parameters' fields
     * @return true if message was sent to at least one client successfully
     */
    public boolean sendMessage(JSONObject message) {
        // Send message to all connected clients
        sendMessageToAll(message);
        
        // Save the message if local storage is enabled
        if (storageService != null) {
            JSONObject storageMessage = new JSONObject();
            long timestamp = System.currentTimeMillis();
            storageMessage.put("id", timestamp);
            storageMessage.put("role", "assistant");
            storageMessage.put("content", message.toString());
            storageMessage.put("datetime", dateFormat.format(new Date(timestamp)));
            storageService.saveMessage(storageMessage);
        }
        return true;
    }

    /**
     * Send a message to all connected WebSocket clients
     */
    private void sendMessageToAll(JSONObject message) {
        if (unifiedServer != null) {
            unifiedServer.sendMessageToAll(message);
        }
    }

    // Removed receiveExactly as it's not used in the current implementation
    
    /**
     * Generates a memory from the conversation history
     * This is called after a certain number of messages have been processed
     */
    private void generateMemory() {
        if (storageService == null) {
            return;
        }
        
        try {
            // Get the latest messages
            List<JSONObject> messages = storageService.getMessages(0, memoryRounds, true);
            
            // Get the latest memory for context
            JSONObject latestMemory = storageService.getLatestMemory();
            String lastMemoryContent = latestMemory != null ? latestMemory.optString("content", "") : "";
            
            // Use HttpUtil to call the summarization API
            String memoryContent = HttpUtil.summarizeConversation(messages, lastMemoryContent);
            
            if (memoryContent != null && !memoryContent.isEmpty()) {
                // Save the new memory
                JSONObject memory = new JSONObject();
                memory.put("type", "long");
                memory.put("content", memoryContent);
                memory.put("datetime", dateFormat.format(new Date()));
                storageService.saveMemory(memory);
                
                LOGGER.info("Generated new memory: " + memoryContent);
            }
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error generating memory: " + e.getMessage(), e);
        }
    }
}
