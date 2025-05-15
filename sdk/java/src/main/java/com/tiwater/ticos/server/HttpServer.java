package com.tiwater.ticos.server;

import com.tiwater.ticos.storage.StorageService;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Simple HTTP server for handling RESTful API requests using Java's built-in HTTP server
 */
public class HttpServer {
    private static final Logger LOGGER = Logger.getLogger(HttpServer.class.getName());
    private final int port;
    private final StorageService storageService;
    private com.sun.net.httpserver.HttpServer server;
    
    public HttpServer(int port, StorageService storageService) {
        this.port = port;
        this.storageService = storageService;
    }
    
    public void start() throws IOException {
        server = com.sun.net.httpserver.HttpServer.create(new InetSocketAddress(port), 0);
        
        // Register handlers
        server.createContext("/memories/latest", this::handleLatestMemoriesRequest);
        
        // Use a thread pool with 10 worker threads
        server.setExecutor(Executors.newFixedThreadPool(10));
        server.start();
        LOGGER.info("HTTP server started on port " + port);
    }
    
    public void stop() {
        if (server != null) {
            server.stop(0);
            LOGGER.info("HTTP server stopped");
        }
    }
    
    private void handleLatestMemoriesRequest(com.sun.net.httpserver.HttpExchange exchange) throws IOException {
        try {
            if (!"GET".equals(exchange.getRequestMethod())) {
                sendResponse(exchange, 405, "Method Not Allowed");
                return;
            }
            
            // Parse query parameters
            String query = exchange.getRequestURI().getQuery();
            int count = 5; // Default value
            
            if (query != null) {
                for (String param : query.split("&")) {
                    String[] pair = param.split("=", 2);
                    if (pair.length == 2 && "count".equals(pair[0])) {
                        try {
                            count = Integer.parseInt(pair[1]);
                            if (count < 1) count = 1;
                            if (count > 100) count = 100; // Limit to 100 messages
                        } catch (NumberFormatException e) {
                            // Use default value if parsing fails
                        }
                    }
                }
            }
            
            // Get latest messages
            List<JSONObject> messages = storageService.getMessages(0, count, false);
            
            // Convert to response format
            JSONArray response = new JSONArray();
            for (JSONObject msg : messages) {
                JSONObject item = new JSONObject();
                item.put("role", msg.optString("role"));
                item.put("content", msg.optString("content"));
                response.put(item);
            }
            
            sendResponse(exchange, 200, response.toString());
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error handling request", e);
            sendResponse(exchange, 500, "Internal Server Error");
        }
    }
    
    private void sendResponse(com.sun.net.httpserver.HttpExchange exchange, int statusCode, String response) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type");
        
        byte[] responseBytes = response.getBytes("UTF-8");
        exchange.sendResponseHeaders(statusCode, responseBytes.length);
        
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(responseBytes);
        }
    }
}
