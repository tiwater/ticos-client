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
import com.tiwater.ticos.SaveMode;

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
    public void initialize() {
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
                        "agent_id = \"\"\n\n" +
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
                LOGGER.error("Error parsing config file:");
                toml.errors().forEach(error -> LOGGER.error(error.toString()));
            }
        } catch (IOException e) {
            // throw new IOException("Failed to initialize config service: " + e.getMessage(), e);
            LOGGER.error("Failed to initialize config service: " + e.getMessage());
        }
    }

    /**
     * Get a configuration value with type safety
     * @param path The path to the configuration value (e.g., "api.host")
     * @param defaultValue The default value to return if the path is not found
     * @return The configuration value or default value
     */
    @SuppressWarnings("unchecked")
    private <T> T get(String path, T defaultValue) {
        try {
            Object value = toml;
            String[] parts = path.split("\\.");
            // Drill down to the parent table of the target value
            for (int i = 0; i < parts.length - 1; i++) {
                if (value instanceof TomlParseResult) {
                    value = ((TomlParseResult) value).getTable(parts[i]);
                } else {
                    return defaultValue;
                }
            }
            // Fetch the actual value from the last part
            if (value instanceof TomlParseResult) {
                Object v = ((TomlParseResult) value).get(parts[parts.length - 1]);
                if (v == null) return defaultValue;
                return (T) v;
            }
            return defaultValue;
        } catch (Exception e) {
            LOGGER.error("Error getting config value for path '" + path + "': " + e.getMessage());
            return defaultValue;
        }
    }
    
    /**
     * Merge two TOML configurations, with the second config taking precedence
     * @param base The base configuration
     * @param override The overriding configuration
     * @return The merged configuration
     */
    private TomlParseResult mergeToml(TomlParseResult base, TomlParseResult override) {
        if (override == null) {
            return base;
        }
        
        // For now, we'll just use the override config if it exists
        // In the future, we can implement a more sophisticated merging strategy
        // that preserves values from the base config that aren't in the override
        return override;
    }

    public String getAgentId() {
        return get("agent_id", "");
    }

    public int getContextRounds() {
        return get("conversation.context_rounds", 6);
    }

    public int getMemoryRounds() {
        return get("conversation.memory_rounds", 18);
    }

    public String getApiHost() {
        return get("api.host", "stardust2.ticos.cn");
    }
    
    public String getApiKey() {
        return get("api.api_key", "");
    }

}
