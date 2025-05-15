package com.tiwater.ticos;

import com.tiwater.ticos.storage.StorageService;
import com.tiwater.ticos.storage.SQLiteStorageService;
import com.tiwater.ticos.util.ConfigUtil;
import org.json.JSONObject;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import static org.junit.Assert.*;

/**
 * Unit tests for TicosClient and related components
 */
public class TicosClientTest {
    private static final String TEST_DB = "test_ticos.db";
    private TicosClient client;
    private StorageService storageService;
    
    @Before
    public void setUp() throws Exception {
        // Delete test database if it exists
        new File(TEST_DB).delete();
        
        // Create a new storage service for testing with test database
        storageService = new SQLiteStorageService(TEST_DB);
        
        // Use different ports for each test to avoid conflicts
        // We'll use a random port between 10000 and 20000
        int testPort = 10000 + (int)(Math.random() * 10000);
        
        // Create a client with test port
        client = new TicosClient(testPort);
        client.enableLocalStorage(storageService);
        client.start();
    }
    
    @After
    public void tearDown() {
        if (client != null) {
            client.stop();
        }
        // Clean up test database
        new File(TEST_DB).delete();
    }
    
    @Test
    public void testMessageStorage() throws Exception {
        // Create a test message
        JSONObject message = new JSONObject();
        message.put("id", "test_msg_1");
        message.put("role", "user");
        message.put("content", "Hello, world!");
        message.put("datetime", "2025-05-15 10:00:00");
        
        // Store the message
        storageService.saveMessage(message);
        
        // Retrieve the message
        JSONObject retrieved = storageService.getMessage("test_msg_1");
        assertNotNull("Message should be retrieved", retrieved);
        assertEquals("Message content should match", "Hello, world!", retrieved.getString("content"));
        
        // Test message retrieval with pagination
        List<JSONObject> messages = storageService.getMessages(0, 10, true);
        assertFalse("Should retrieve messages", messages.isEmpty());
        assertEquals("Should retrieve the test message", "test_msg_1", messages.get(0).getString("id"));
    }
    
    @Test
    public void testMemoryStorage() throws Exception {
        // Create a test memory
        JSONObject memory = new JSONObject();
        memory.put("type", "long");
        memory.put("content", "Test memory content");
        memory.put("datetime", "2025-05-15 10:00:00");
        
        // Store the memory
        storageService.saveMemory(memory);
        
        // Get the latest memory
        JSONObject latest = storageService.getLatestMemory();
        assertNotNull("Latest memory should be retrieved", latest);
        assertEquals("Memory content should match", "Test memory content", latest.getString("content"));
    }
    
    @Test
    public void testMessageHandling() throws Exception {
        // Clear any existing messages
        if (storageService instanceof SQLiteStorageService) {
            SQLiteStorageService sqliteStorage = (SQLiteStorageService) storageService;
            try (Connection connection = DriverManager.getConnection(sqliteStorage.getDbUrl());
                 Statement stmt = connection.createStatement()) {
                stmt.execute("DELETE FROM messages");
            }
        }
        
        // Simulate receiving a message
        JSONObject message = new JSONObject()
            .put("name", "test_message")
            .put("arguments", new JSONObject()
                .put("content", "Test message content"));
        
        // The client should automatically save this message
        client.sendMessage(message);
        
        // Give it a moment to process
        Thread.sleep(100);
        
        // Verify the message was stored
        List<JSONObject> messages = storageService.getMessages(0, 10, true);
        assertFalse("Should have stored the message", messages.isEmpty());
        
        // Get the stored message
        JSONObject storedMessage = messages.get(0);
        
        // Debug log the stored message structure
        System.out.println("Stored message: " + storedMessage.toString(2));
        
        // The content should be a string
        String content = storedMessage.optString("content");
        assertNotNull("Content should not be null", content);
        
        // The content should be the string representation of the original message
        JSONObject contentObj = new JSONObject(content);
        assertEquals("Should have the test message content", 
            "Test message content", 
            contentObj.getJSONObject("arguments").getString("content"));
        assertEquals("Should have the correct message type",
            "test_message",
            contentObj.getString("name"));
    }
    
    @Test
    public void testConfigUtil() {
        // Test default values
        assertEquals("Default API host should match", "stardust2.ticos.cn", ConfigUtil.getApiHost());
        assertEquals("Default memory rounds should be 18", 18, ConfigUtil.getMemoryRounds());
    }
}
