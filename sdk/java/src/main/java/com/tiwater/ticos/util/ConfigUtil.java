package com.tiwater.ticos.util;

import org.tomlj.Toml;
import org.tomlj.TomlParseResult;
import org.tomlj.TomlTable;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Utility class for reading TOML configuration files
 */
public class ConfigUtil {
    private static final Logger LOGGER = Logger.getLogger(ConfigUtil.class.getName());
    private static final String CONFIG_DIR = System.getProperty("user.home") + "/.config/ticos";
    private static final String CONFIG_FILE = "config.toml";
    private static TomlParseResult toml;
    
    static {
        try {
            // Create config directory if it doesn't exist
            Path configDir = Paths.get(CONFIG_DIR);
            if (!Files.exists(configDir)) {
                Files.createDirectories(configDir);
            }
            
            // Create default config file if it doesn't exist
            Path configFile = Paths.get(CONFIG_DIR, CONFIG_FILE);
            if (!Files.exists(configFile)) {
                // Create a default config
                String defaultConfig = "# Ticos Client Configuration\n" +
                        "agent_id = \"\"\n\n" +
                        "[microphone]\n" +
                        "component = \"pulsesrc\"\n" +
                        "device = \"\"\n\n" +
                        "[speaker]\n" +
                        "component = \"pulsesink\"\n" +
                        "device = \"\"\n\n" +
                        "[camera]\n" +
                        "enable = false\n" +
                        "component = \"v4l2src\"\n" +
                        "device = \"\"\n" +
                        "upload_enabled = false\n" +
                        "visualvoice_enabled = false\n\n" +
                        "[conversation]\n" +
                        "context_rounds = 6\n" +
                        "memory_rounds = 18\n\n" +
                        "[api]\n" +
                        "host = \"stardust2.ticos.cn\"\n" +
                        "api_key = \"\"\n" +
                        "protocol = \"wss\"";
                
                Files.writeString(configFile, defaultConfig);
                LOGGER.warning("Config file not found, created default config at: " + configFile);
            }
            
            // Load the config file
            toml = Toml.parse(configFile);
            
            if (toml.hasErrors()) {
                LOGGER.severe("Error parsing config file:");
                toml.errors().forEach(error -> LOGGER.severe(error.toString()));
            }
            
        } catch (IOException e) {
            LOGGER.log(Level.SEVERE, "Failed to load config file: " + e.getMessage(), e);
            // Use empty config if file can't be loaded
            toml = Toml.parse("");
        }
    }
    
    @SuppressWarnings("unchecked")
    private static <T> T get(String path, T defaultValue) {
        try {
            Object value = toml;
            String[] parts = path.split("\\.");
            
            for (String part : parts) {
                if (value instanceof TomlTable) {
                    value = ((TomlTable) value).get(part);
                } else {
                    return defaultValue;
                }
                
                if (value == null) {
                    return defaultValue;
                }
            }
            
            if (value != null) {
                if (defaultValue instanceof Integer) {
                    if (value instanceof Long) {
                        return (T) Integer.valueOf(((Long) value).intValue());
                    } else if (value instanceof Integer) {
                        return (T) value;
                    }
                } else if (value.getClass().isInstance(defaultValue)) {
                    return (T) value;
                } else if (defaultValue instanceof String) {
                    return (T) String.valueOf(value);
                }
            }
        } catch (Exception e) {
            LOGGER.log(Level.WARNING, "Error reading config value: " + path, e);
        }
        return defaultValue;
    }
    
    public static String getAgentId() {
        return get("agent_id", "");
    }
    
    public static int getContextRounds() {
        return get("conversation.context_rounds", 6);
    }
    
    public static int getMemoryRounds() {
        return get("conversation.memory_rounds", 18);
    }
    
    public static String getApiHost() {
        return get("api.host", "stardust2.ticos.cn");
    }
    
    public static String getApiKey() {
        return get("api.api_key", "");
    }
    
    public static String getApiProtocol() {
        return get("api.protocol", "wss");
    }
    
    public static String getMicrophoneDevice() {
        return get("microphone.device", "");
    }
    
    public static String getMicrophoneComponent() {
        return get("microphone.component", "pulsesrc");
    }
    
    public static String getSpeakerDevice() {
        return get("speaker.device", "");
    }
    
    public static String getSpeakerComponent() {
        return get("speaker.component", "pulsesink");
    }
    
    public static boolean isCameraEnabled() {
        return get("camera.enable", false);
    }
    
    public static String getCameraDevice() {
        return get("camera.device", "");
    }
    
    public static String getCameraComponent() {
        return get("camera.component", "v4l2src");
    }
    
    public static boolean isUploadEnabled() {
        return get("camera.upload_enabled", false);
    }
    
    public static boolean isVisualVoiceEnabled() {
        return get("camera.visualvoice_enabled", false);
    }
}
