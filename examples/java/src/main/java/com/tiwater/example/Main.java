package com.tiwater.example;

import com.tiwater.ticos.TicosClient;
import org.json.JSONObject;
import java.util.Random;
import java.util.logging.Logger;

public class Main {
    private static final Logger LOGGER = Logger.getLogger(Main.class.getName());
    private static final Random random = new Random();

    public static void main(String[] args) {
        // Create and start the client
        TicosClient client = new TicosClient(9999);
        
        // Set message handlers
        client.setMessageHandler(message -> 
            LOGGER.info("Received message: " + message.toString()));
            
        client.setMotionHandler(parameters -> 
            LOGGER.info("Received motion command with parameters: " + parameters.toString()));
            
        client.setEmotionHandler(parameters -> 
            LOGGER.info("Received emotion command with parameters: " + parameters.toString()));

        if (!client.start()) {
            LOGGER.severe("Failed to start client");
            return;
        }

        try {
            // Keep the main thread running and send heartbeat
            while (true) {
                // Send heartbeat message
                JSONObject heartbeat = new JSONObject()
                    .put("name", "heartbeat")
                    .put("arguments", new JSONObject()
                        .put("timestamp", System.currentTimeMillis()));
                
                if (client.sendMessage(heartbeat)) {
                    LOGGER.info("Heartbeat sent");
                }

                Thread.sleep(2000);
            }
        } catch (InterruptedException e) {
            LOGGER.info("Client interrupted");
        } finally {
            client.stop();
        }
    }
}
