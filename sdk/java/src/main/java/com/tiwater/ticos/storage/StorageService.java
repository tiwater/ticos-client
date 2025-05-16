package com.tiwater.ticos.storage;

import org.json.JSONObject;
import java.util.List;

/**
 * Interface defining storage operations for messages and memories
 */
public interface StorageService {
    /**
     * Initialize the storage service.
     * This method must be called after setting up any configuration (like TF card directory).
     * @throws IOException if initialization fails
     */
    void initialize() throws IOException;
    void setStoreRootDir(String tfRootDir);
    // Message operations
    boolean saveMessage(JSONObject message);
    JSONObject getMessage(String id);
    boolean updateMessage(String id, JSONObject message);
    boolean deleteMessage(String id);
    List<JSONObject> getMessages(int offset, int limit, boolean ascending);
    
    // Memory operations
    boolean saveMemory(JSONObject memory);
    JSONObject getMemory(long id);
    boolean updateMemory(long id, JSONObject memory);
    boolean deleteMemory(long id);
    JSONObject getLatestMemory();
}
