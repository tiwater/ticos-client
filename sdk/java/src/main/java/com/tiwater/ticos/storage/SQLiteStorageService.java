package com.tiwater.ticos.storage;

import org.json.JSONObject;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * SQLite implementation of StorageService
 */
public class SQLiteStorageService implements StorageService {
    private static final Logger LOGGER = Logger.getLogger(SQLiteStorageService.class.getName());
    private static final String DEFAULT_DB_NAME = "ticos.db";
    private static final String DEFAULT_CONFIG_DIR = System.getProperty("user.home") + "/.config/ticos";
    private String tfConfigDir = null;
    private String dbUrl;
    private Connection connection;

    /**
     * Set the TF card configuration directory for data storage
     * @param tfRootDir The root directory of the TF card
     */
    public void setTfRootDir(String tfRootDir) {
        if (tfRootDir != null) {
            this.tfConfigDir = Paths.get(tfRootDir, ".config", "ticos").toString();
        } else {
            this.tfConfigDir = null;
        }
    }
    
    /**
     * Get the database URL for this storage service.
     * @return The JDBC URL for the database
     */
    public String getDbUrl() {
        return dbUrl;
    }
    private static final String CREATE_MESSAGES_TABLE = 
        "CREATE TABLE IF NOT EXISTS messages (" +
        "id TEXT PRIMARY KEY," +
        "role TEXT NOT NULL," +
        "content TEXT NOT NULL," +
        "datetime TEXT NOT NULL" +
        ")";
    
    private static final String CREATE_MEMORIES_TABLE = 
        "CREATE TABLE IF NOT EXISTS memories (" +
        "id INTEGER PRIMARY KEY AUTOINCREMENT," +
        "type TEXT NOT NULL," +
        "content TEXT NOT NULL," +
        "datetime TEXT NOT NULL" +
        ")";
    
    /**
     * Creates a new SQLiteStorageService with the default database name.
     * The storage service must be initialized using initialize() before use.
     */
    public SQLiteStorageService() {
        // No initialization here, must call initialize() after setup
    }
    
    @Override
    public void initialize() throws Exception {
        try {
            // Load SQLite JDBC driver
            Class.forName("org.sqlite.JDBC");
            
            // Create config directory if it doesn't exist
            Path configDir = tfConfigDir != null ? Paths.get(tfConfigDir) : Paths.get(DEFAULT_CONFIG_DIR);
            if (!Files.exists(configDir)) {
                Files.createDirectories(configDir);
                LOGGER.info("Created config directory: " + configDir);
            }
            
            // Set the database URL
            String dbPath = Paths.get(configDir.toString(), DEFAULT_DB_NAME).toString();
            this.dbUrl = "jdbc:sqlite:" + dbPath;
            LOGGER.info("Using database at: " + dbPath);
            
            // Initialize database
            connection = DriverManager.getConnection(dbUrl);
            try (Statement stmt = connection.createStatement()) {
                stmt.execute(CREATE_MESSAGES_TABLE);
                stmt.execute(CREATE_MEMORIES_TABLE);
            }
        } catch (SQLException | ClassNotFoundException e) {
            throw new IOException("Failed to initialize database: " + e.getMessage(), e);
        }
    }
    
    @Override
    public boolean saveMessage(JSONObject message) {
        String sql = "INSERT OR REPLACE INTO messages (id, role, content, datetime) VALUES (?, ?, ?, ?)";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, message.optString("id"));
            pstmt.setString(2, message.optString("role"));
            pstmt.setString(3, message.optString("content"));
            pstmt.setString(4, message.optString("datetime"));
            pstmt.executeUpdate();
            return true;
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to save message: " + e.getMessage(), e);
            return false;
        }
    }
    
    @Override
    public JSONObject getMessage(String id) {
        String sql = "SELECT * FROM messages WHERE id = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, id);
            ResultSet rs = pstmt.executeQuery();
            if (rs.next()) {
                return resultSetToJson(rs);
            }
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to get message: " + e.getMessage(), e);
        }
        return null;
    }
    
    @Override
    public boolean updateMessage(String id, JSONObject message) {
        String sql = "UPDATE messages SET role = ?, content = ?, datetime = ? WHERE id = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, message.optString("role"));
            pstmt.setString(2, message.optString("content"));
            pstmt.setString(3, message.optString("datetime"));
            pstmt.setString(4, id);
            int updated = pstmt.executeUpdate();
            return updated > 0;
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to update message: " + e.getMessage(), e);
            return false;
        }
    }
    
    @Override
    public boolean deleteMessage(String id) {
        String sql = "DELETE FROM messages WHERE id = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, id);
            int deleted = pstmt.executeUpdate();
            return deleted > 0;
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to delete message: " + e.getMessage(), e);
            return false;
        }
    }
    
    @Override
    public List<JSONObject> getMessages(int offset, int limit, boolean ascending) {
        List<JSONObject> messages = new ArrayList<>();
        String order = ascending ? "ASC" : "DESC";
        String sql = String.format("SELECT * FROM messages ORDER BY datetime %s LIMIT ? OFFSET ?", order);
        
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setInt(1, limit);
            pstmt.setInt(2, offset);
            ResultSet rs = pstmt.executeQuery();
            
            while (rs.next()) {
                messages.add(resultSetToJson(rs));
            }
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to get messages: " + e.getMessage(), e);
        }
        
        return messages;
    }
    
    @Override
    public boolean saveMemory(JSONObject memory) {
        String sql = "INSERT INTO memories (type, content, datetime) VALUES (?, ?, ?)";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, memory.optString("type"));
            pstmt.setString(2, memory.optString("content"));
            pstmt.setString(3, memory.optString("datetime"));
            pstmt.executeUpdate();
            
            // Get the last inserted row ID using SQLite's last_insert_rowid()
            try (Statement stmt = connection.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT last_insert_rowid()")) {
                if (rs.next()) {
                    memory.put("id", rs.getLong(1));
                }
            }
            return true;
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to save memory: " + e.getMessage(), e);
            return false;
        }
    }
    
    @Override
    public JSONObject getMemory(long id) {
        String sql = "SELECT * FROM memories WHERE id = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setLong(1, id);
            ResultSet rs = pstmt.executeQuery();
            if (rs.next()) {
                return resultSetToJson(rs);
            }
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to get memory: " + e.getMessage(), e);
        }
        return null;
    }
    
    @Override
    public boolean updateMemory(long id, JSONObject memory) {
        String sql = "UPDATE memories SET type = ?, content = ?, datetime = ? WHERE id = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setString(1, memory.optString("type"));
            pstmt.setString(2, memory.optString("content"));
            pstmt.setString(3, memory.optString("datetime"));
            pstmt.setLong(4, id);
            int updated = pstmt.executeUpdate();
            return updated > 0;
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to update memory: " + e.getMessage(), e);
            return false;
        }
    }
    
    @Override
    public boolean deleteMemory(long id) {
        String sql = "DELETE FROM memories WHERE id = ?";
        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            pstmt.setLong(1, id);
            int deleted = pstmt.executeUpdate();
            return deleted > 0;
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to delete memory: " + e.getMessage(), e);
            return false;
        }
    }
    
    @Override
    public JSONObject getLatestMemory() {
        String sql = "SELECT * FROM memories ORDER BY id DESC LIMIT 1";
        try (Statement stmt = connection.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            if (rs.next()) {
                return resultSetToJson(rs);
            }
        } catch (SQLException e) {
            LOGGER.log(Level.SEVERE, "Failed to get latest memory: " + e.getMessage(), e);
        }
        return null;
    }
    
    private JSONObject resultSetToJson(ResultSet rs) throws SQLException {
        JSONObject json = new JSONObject();
        ResultSetMetaData metaData = rs.getMetaData();
        int columnCount = metaData.getColumnCount();
        
        for (int i = 1; i <= columnCount; i++) {
            String columnName = metaData.getColumnLabel(i);
            Object value = rs.getObject(i);
            
            // Special handling for content field which might be a JSON string
            if ("content".equalsIgnoreCase(columnName) && value instanceof String) {
                try {
                    // Try to parse the content as JSON
                    json.put(columnName, new JSONObject((String) value));
                } catch (Exception e) {
                    // If parsing fails, just use the string value
                    json.put(columnName, value);
                }
            } else {
                json.put(columnName, value);
            }
        }
        
        return json;
    }
}
