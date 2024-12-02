package com.tiwater.example;

import com.tiwater.ticos.TicosClient;
import org.json.JSONObject;

public class Main {

    public static void main(String[] args) {
        // Create and start the server
        TicosClient server = new TicosClient(9999);
        
        // Set message handlers
        server.setMessageHandler(message -> 
            System.out.println("Received message: " + message.toString()));
        
        server.setMotionHandler(motionId -> 
            System.out.println("Received motion command: " + motionId));
        
        server.setEmotionHandler(emotionId -> 
            System.out.println("Received emotion command: " + emotionId));

        if (!server.start()) {
            System.out.println("Failed to start server");
            return;
        }

        // Keep sending heartbeat messages
        try {
            while (true) {
                JSONObject heartbeat = new JSONObject()
                    .put("type", "heartbeat")
                    .put("timestamp", System.currentTimeMillis());
                
                server.sendMessage(heartbeat);
                Thread.sleep(5000);
            }
        } catch (InterruptedException e) {
            System.out.println("Server interrupted");
        } finally {
            server.stop();
        }
    }
}
