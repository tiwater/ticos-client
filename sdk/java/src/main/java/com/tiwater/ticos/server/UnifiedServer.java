package com.tiwater.ticos.server;

import com.tiwater.ticos.MessageCallbackInterface;
import com.tiwater.ticos.storage.StorageService;
import io.undertow.Undertow;
import io.undertow.server.HttpHandler;
import io.undertow.server.HttpServerExchange;
import io.undertow.server.handlers.PathHandler;
import io.undertow.util.Headers;
import io.undertow.util.HttpString;
import io.undertow.util.StatusCodes;
import io.undertow.websockets.WebSocketConnectionCallback;
import io.undertow.websockets.core.*;
import io.undertow.websockets.spi.WebSocketHttpExchange;
import org.json.JSONArray;
import org.json.JSONObject;
import org.xnio.OptionMap;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.logging.Level;
import java.util.logging.Logger;

import static io.undertow.Handlers.path;
import static io.undertow.Handlers.websocket;

/**
 * Unified server that provides both HTTP and WebSocket services on the same port
 */
public class UnifiedServer {
    private static final Logger LOGGER = Logger.getLogger(UnifiedServer.class.getName());
    private final int port;
    private final MessageCallbackInterface messageCallback;
    private final StorageService storageService;
    private Undertow server;
    private final Set<WebSocketChannel> webSocketConnections = new CopyOnWriteArraySet<>();
    
    public UnifiedServer(int port, MessageCallbackInterface messageCallback, StorageService storageService) {
        this.port = port;
        this.messageCallback = messageCallback;
        this.storageService = storageService;
    }
    
    public void start() {
        // Create WebSocket connection callback
        WebSocketConnectionCallback wsCallback = new WebSocketConnectionCallback() {
            @Override
            public void onConnect(WebSocketHttpExchange exchange, WebSocketChannel channel) {
                webSocketConnections.add(channel);
                LOGGER.info("WebSocket client connected: " + channel.getPeerAddress());
                
                // Set up message handler
                channel.getReceiveSetter().set(new AbstractReceiveListener() {
                    @Override
                    protected void onFullTextMessage(WebSocketChannel channel, BufferedTextMessage message) {
                        String messageText = message.getData();
                        try {
                            JSONObject jsonMessage = new JSONObject(messageText);
                            messageCallback.handleMessage(jsonMessage);
                        } catch (Exception e) {
                            LOGGER.log(Level.SEVERE, "Error processing WebSocket message: " + e.getMessage(), e);
                        }
                    }
                    
                    @Override
                    protected void onError(WebSocketChannel channel, Throwable error) {
                        LOGGER.log(Level.SEVERE, "WebSocket error: " + error.getMessage(), error);
                        webSocketConnections.remove(channel);
                    }
                    
                    @Override
                    protected void onClose(WebSocketChannel webSocketChannel, StreamSourceFrameChannel channel) throws IOException {
                        super.onClose(webSocketChannel, channel);
                        webSocketConnections.remove(webSocketChannel);
                    }
                });
                
                channel.resumeReceives();
            }
        };
        
        // Create path handler with WebSocket endpoint
        PathHandler pathHandler = path()
            // WebSocket endpoint
            .addPrefixPath("/realtime", websocket(wsCallback))
            
            // HTTP endpoints
            .addExactPath("/memories/latest", exchange -> {
                if (exchange.isInIoThread()) {
                    exchange.dispatch(exchange1 -> handleMemoriesRequest(exchange1));
                    return;
                }
                handleMemoriesRequest(exchange);
            });

        // Initialize and start the server
        server = Undertow.builder()
                .addHttpListener(port, "0.0.0.0")
                .setHandler(pathHandler)
                .build();
        
        server.start();
        LOGGER.info("Unified server started on port " + port);
    }
    
    private void handleMemoriesRequest(HttpServerExchange exchange) {
        if (exchange.getRequestMethod().toString().equals("GET")) {
            // Parse query parameters
            String countParam = exchange.getQueryParameters().get("count") != null ? 
                               exchange.getQueryParameters().get("count").getFirst() : "5";
            int count = 5; // Default value
            
            try {
                count = Integer.parseInt(countParam);
                if (count < 1) count = 1;
                if (count > 100) count = 100; // Limit to 100 messages
            } catch (NumberFormatException e) {
                // Use default value if parsing fails
            }
            
            // Get latest messages
            List<JSONObject> messages = storageService.getMessages(0, count, false);

            // Reverse the array to get oldest first
            Collections.reverse(messages);
            
            // Convert to response format
            JSONArray response = new JSONArray();
            for (JSONObject msg : messages) {
                JSONObject item = new JSONObject();
                item.put("role", msg.optString("role"));
                
                // Try to parse content as JSON
                String content = msg.optString("content");
                try {
                    JSONObject contentJson = new JSONObject(content);
                    item.put("content", contentJson);
                } catch (Exception e) {
                    // If parsing fails, use the original string
                    item.put("content", content);
                }
                
                response.put(item);
            }
            
            sendJsonResponse(exchange, 200, response.toString());
        } else {
            sendJsonResponse(exchange, 405, "{\"error\":\"Method not allowed\"}");
        }
    }
    
    public void stop() {
        if (server != null) {
            server.stop();
            LOGGER.info("Unified server stopped");
        }
    }
    
    public void sendMessageToAll(JSONObject message) {
        String messageText = message.toString();
        for (WebSocketChannel channel : webSocketConnections) {
            try {
                WebSockets.sendText(messageText, channel, null);
            } catch (Exception e) {
                LOGGER.log(Level.SEVERE, "Failed to send message to client: " + e.getMessage(), e);
            }
        }
    }
    
    public void sendMessageToClient(JSONObject message, WebSocketChannel client) {
        try {
            WebSockets.sendText(message.toString(), client, null);
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Failed to send message to client: " + e.getMessage(), e);
        }
    }
    
    private void sendJsonResponse(HttpServerExchange exchange, int statusCode, String jsonResponse) {
        exchange.setStatusCode(statusCode);
        exchange.getResponseHeaders().put(Headers.CONTENT_TYPE, "application/json");
        exchange.getResponseHeaders().put(new HttpString("Access-Control-Allow-Origin"), "*");
        exchange.getResponseHeaders().put(new HttpString("Access-Control-Allow-Methods"), "GET, OPTIONS");
        exchange.getResponseHeaders().put(new HttpString("Access-Control-Allow-Headers"), "Content-Type");
        exchange.getResponseSender().send(jsonResponse);
    }
}
