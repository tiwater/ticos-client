package com.tiwater.ticos.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.tomlj.Toml;
import org.tomlj.TomlParseResult;
import org.tomlj.TomlTable;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class ConfigService {
    private static final Logger LOGGER = LoggerFactory.getLogger(ConfigService.class);
    private static final String CONFIG_FILE = "config.toml";
    private final String userConfigDir;
    private final String tfConfigDir;
    private TomlParseResult toml;
    private final SaveMode saveMode;

    /**
     * Creates a new ConfigService with the specified save mode and optional TF card root directory
     * @param saveMode The save mode (INTERNAL or EXTERNAL)
     * @param tfRootDir The root directory of the TF card, or null if using internal storage
     */
    public ConfigService(SaveMode saveMode, String tfRootDir) {
        this.saveMode = saveMode;
        this.userConfigDir = System.getProperty("user.home") + "/.config/ticos";
        this.tfConfigDir = tfRootDir != null ? 
            Paths.get(tfRootDir, ".config", "ticos").toString() :
            null;

        initialize();
    }

    /**
     * Initializes the configuration service.
     * This method must be called after the instance is created.
     * @throws IOException if initialization fails
     */
    public void initialize() throws IOException {
        try {
            // Always create user config directory
            Path userConfigDirPath = Paths.get(userConfigDir);
            if (!Files.exists(userConfigDirPath)) {
                Files.createDirectories(userConfigDirPath);
                LOGGER.info("Created user config directory: " + userConfigDirPath);
            }

            // Create default user config if it doesn't exist
            Path userConfigFile = userConfigDirPath.resolve(CONFIG_FILE);
            if (!Files.exists(userConfigFile)) {
                String defaultConfig = "# Ticos Client Configuration\n" +
                        "agent_id = \"\"\n\n"
                        "[conversation]\n" +
                        "context_rounds = 6\n" +
                        "memory_rounds = 18\n\n";
                
                Files.writeString(userConfigFile, defaultConfig);
                LOGGER.info("Created default user config at: " + userConfigFile);
            }

            // Load user config
            TomlParseResult userToml = Toml.parse(userConfigFile);
            
            // If TF config directory is set, try to merge with TF config
            if (tfConfigDir != null) {
                Path tfConfigDirPath = Paths.get(tfConfigDir);
                if (!Files.exists(tfConfigDirPath)) {
                    Files.createDirectories(tfConfigDirPath);
                    LOGGER.info("Created TF config directory: " + tfConfigDirPath);
                }

                Path tfConfigFile = tfConfigDirPath.resolve(CONFIG_FILE);
                TomlParseResult tfToml = null;
                
                // If TF config file exists, load and merge it
                if (Files.exists(tfConfigFile)) {
                    tfToml = Toml.parse(tfConfigFile);
                    LOGGER.info("Loaded TF config from: " + tfConfigFile);
                }
                
                // Merge configs (TF config takes precedence)
                toml = mergeToml(userToml, tfToml);
            } else {
                toml = userToml;
            }

            if (toml.hasErrors()) {
                LOGGER.severe("Error parsing config file:");
                toml.errors().forEach(error -> LOGGER.severe(error.toString()));
            }
        } catch (IOException e) {
            throw new IOException("Failed to initialize config service: " + e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T get(String path, T defaultValue) {
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
            LOGGER.warn("Error reading config value: " + path, e);
        }
        return defaultValue;
    }

    /**
     * Merge two TOML configurations, with the second config taking precedence
     * @param base The base configuration
     * @param override The overriding configuration
     * @return The merged configuration
     */
    private static TomlParseResult mergeToml(TomlParseResult base, TomlParseResult override) {
        if (override == null) {
            return base;
        }
        
        // Create a new TOML table to hold the merged configuration
        TomlTable merged = new TomlTable();
        
        // First add all values from the base configuration
        base.getTable().forEach((key, value) -> {
            if (value instanceof TomlTable) {
                merged.put(key, new TomlTable());
                ((TomlTable) value).forEach((subKey, subValue) -> 
                    ((TomlTable) merged.get(key)).put(subKey, subValue));
            } else {
                merged.put(key, value);
            }
        });
        
        // Then override with values from the override configuration
        override.getTable().forEach((key, value) -> {
            if (value instanceof TomlTable) {
                if (!merged.containsKey(key)) {
                    merged.put(key, new TomlTable());
                }
                ((TomlTable) value).forEach((subKey, subValue) -> 
                    ((TomlTable) merged.get(key)).put(subKey, subValue));
            } else {
                merged.put(key, value);
            }
        });
        
        return new TomlParseResult(merged, null);
    }

    public int getContextRounds() {
        return get("conversation.context_rounds", 6);
    }

    public int getMemoryRounds() {
        return get("conversation.memory_rounds", 18);
    }

}
