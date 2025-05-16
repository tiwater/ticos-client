package com.tiwater.ticos.storage;

import org.json.JSONObject;
import java.util.List;
import java.io.IOException;

/**
 * Interface defining storage operations for messages and memories
 */
public interface StorageService {
    /**
     * Set the root directory for storage.
     * 
     * @param tfRootDir The root directory of the TF card
     */
    void setStoreRootDir(String tfRootDir);
    
    /**
     * Initialize the storage service.
     * This method must be called after setting up any configuration (like TF card directory).
     * @throws IOException if initialization fails
     */
    void initialize() throws IOException;
    
    // Message operations
    /**
     * Save a message to storage.
     */
    boolean saveMessage(JSONObject message);
    
    /**
     * Get a message from storage.
     */
    JSONObject getMessage(String id);
    
    /**
     * Update a message in storage.
     */
    boolean updateMessage(String id, JSONObject message);
    
    /**
     * Delete a message from storage.
     */
    boolean deleteMessage(String id);
    
    /**
     * Get messages from storage with pagination.
     */
    List<JSONObject> getMessages(int offset, int limit, boolean ascending);
    
    // Memory operations
    /**
     * Save a memory to storage.
     */
    boolean saveMemory(JSONObject memory);
    
    /**
     * Get a memory from storage.
     */
    JSONObject getMemory(long id);
    
    /**
     * Update a memory in storage.
     */
    boolean updateMemory(long id, JSONObject memory);
    
    /**
     * Delete a memory from storage.
     */
    boolean deleteMemory(long id);
    
    /**
     * Get the latest memory.
     */
    JSONObject getLatestMemory();
}
