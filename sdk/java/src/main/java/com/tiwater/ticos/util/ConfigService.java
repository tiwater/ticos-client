package com.tiwater.ticos.util;

import java.util.logging.Level;
import java.util.logging.Logger;
import org.tomlj.Toml;
import org.tomlj.TomlParseResult;
import org.tomlj.TomlTable;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;
import com.tiwater.ticos.SaveMode;

public class ConfigService {
    private static final Logger LOGGER = Logger.getLogger(ConfigService.class.getName());
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
                
            // Log the final merged configuration
            StringBuilder configLog = new StringBuilder("Final merged configuration:\n");
            logTomlTable(configLog, toml, "  ");
            LOGGER.info(configLog.toString());


            if (toml.hasErrors()) {
                LOGGER.severe("Error parsing config file:");
                toml.errors().forEach(error -> LOGGER.severe(error.toString()));
            }
        } catch (IOException e) {
            // throw new IOException("Failed to initialize config service: " + e.getMessage(), e);
            LOGGER.severe("Failed to initialize config service: " + e.getMessage());
        }
    }


    /**
     * 递归打印 TomlTable 内容到 StringBuilder
     */
    private void logTomlTable(StringBuilder sb, TomlTable table, String prefix) {
        for (String key : table.keySet()) {
            Object value = table.get(key);
            if (value instanceof TomlTable) {
                sb.append(prefix).append(key).append(":\n");
                logTomlTable(sb, (TomlTable) value, prefix + "  ");
            } else {
                sb.append(prefix).append(key).append(" = ").append(value).append("\n");
            }
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
            String[] parts = path.split("\\.");
            TomlTable table = toml;
            for (int i = 0; i < parts.length - 1; i++) {
                Object next = table.get(parts[i]);
                if (next instanceof TomlTable) {
                    table = (TomlTable) next;
                } else {
                    return defaultValue;
                }
            }
            Object value = table.get(parts[parts.length - 1]);
            if (value == null) return defaultValue;
            // 自动将 Long 转为 Integer
            if (defaultValue instanceof Integer && value instanceof Long) {
                return (T) Integer.valueOf(((Long) value).intValue());
            }
            return (T) value;
        } catch (Exception e) {
            LOGGER.severe("Error getting config value for path '" + path + "': " + e.getMessage());
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
        if (base == null) return override;
        if (override == null) return base;
        Map<String, Object> merged = deepMerge(toMap(base), toMap(override));
        String tomlString = mapToTomlString(merged);
        return Toml.parse(tomlString);
    }

    // 将 TomlTable/TomlParseResult 转为 Map
    private Map<String, Object> toMap(TomlTable table) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (String key : table.keySet()) {
            Object value = table.get(key);
            if (value instanceof TomlTable) {
                map.put(key, toMap((TomlTable) value));
            } else {
                map.put(key, value);
            }
        }
        return map;
    }

    // 递归合并两个 Map
    private Map<String, Object> deepMerge(Map<String, Object> base, Map<String, Object> override) {
        Map<String, Object> result = new LinkedHashMap<>(base);
        for (Map.Entry<String, Object> entry : override.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();
            if (value instanceof Map && base.get(key) instanceof Map) {
                result.put(key, deepMerge((Map<String, Object>) base.get(key), (Map<String, Object>) value));
            } else {
                result.put(key, value);
            }
        }
        return result;
    }

    // Map 转 TOML 字符串（简单实现，适合本项目结构）
    private String mapToTomlString(Map<String, Object> map) {
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (entry.getValue() instanceof Map) {
                sb.append("[").append(entry.getKey()).append("]\n");
                Map<String, Object> subMap = (Map<String, Object>) entry.getValue();
                for (Map.Entry<String, Object> subEntry : subMap.entrySet()) {
                    sb.append(subEntry.getKey()).append(" = ").append(formatTomlValue(subEntry.getValue())).append("\n");
                }
            } else {
                sb.append(entry.getKey()).append(" = ").append(formatTomlValue(entry.getValue())).append("\n");
            }
        }
        return sb.toString();
    }

    private String formatTomlValue(Object value) {
        if (value instanceof String) {
            return "\"" + value + "\"";
        }
        return String.valueOf(value);
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
