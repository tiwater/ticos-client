package com.tiwater.ticos.util;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;
import com.tiwater.ticos.util.ConfigService;

/**
 * Utility class for making HTTP requests
 */
public class HttpUtil {
    private static final Logger LOGGER = Logger.getLogger(HttpUtil.class.getName());
    
    /**
     * Send a POST request to the summarization API
     * @param conversationHistory List of conversation messages
     * @param lastMemory Last memory content
     * @return Summary text or null if failed
     */
    public static String summarizeConversation(List<JSONObject> conversationHistory, String lastMemory, ConfigService configService) {
        try {
            String apiUrl = "https://" + configService.getApiHost() + "/summarize";
            String apiKey = configService.getApiKey();
            
            if (apiKey == null || apiKey.isEmpty()) {
                LOGGER.warning("API key is not configured");
                return null;
            }
            
            // Prepare request body
            JSONObject requestBody = new JSONObject();
            JSONArray historyArray = new JSONArray();
            
            for (JSONObject message : conversationHistory) {
                JSONObject msg = new JSONObject();
                msg.put("role", message.optString("role"));
                msg.put("content", message.optString("content"));
                historyArray.put(msg);
            }
            
            requestBody.put("conversation_history", historyArray);
            
            JSONObject parameters = new JSONObject();
            parameters.put("max_length", 1024);
            parameters.put("summarize_prompt", 
                "这是之前的记忆：" + (lastMemory != null ? lastMemory : "") + 
                ", 总结上述对话，作为长期记忆供客户端保存。");
            
            requestBody.put("parameters", parameters);
            
            // Create and configure connection
            URL url = new URL(apiUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Proxy-Authorization", "Bearer " + apiKey);
            conn.setDoOutput(true);
            
            // Send request
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = requestBody.toString().getBytes(StandardCharsets.UTF_8);
                os.write(input, 0, input.length);
            }
            
            // Get response
            int responseCode = conn.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                String response = new String(conn.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
                JSONObject jsonResponse = new JSONObject(response);
                JSONArray summaryArray = jsonResponse.getJSONArray("summary");
                // Join all summary parts with spaces
                StringBuilder summary = new StringBuilder();
                for (int i = 0; i < summaryArray.length(); i++) {
                    if (i > 0) summary.append(" ");
                    summary.append(summaryArray.getString(i));
                }
                return summary.toString();
            } else {
                LOGGER.warning("Failed to get summary. Status code: " + responseCode);
                return null;
            }
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error calling summarization API: " + e.getMessage(), e);
            return null;
        }
    }
}
