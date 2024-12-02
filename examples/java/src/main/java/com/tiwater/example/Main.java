package com.tiwater.example;

import com.tiwater.ticos.TicosClient;
import org.json.JSONObject;

public class Main {

    public static void main(String[] args) {
        // Create and start the client
        TicosClient client = new TicosClient(9999);
        
        // Set message handlers
        client.setMessageHandler(message -> 
            System.out.println("Received message: " + message.toString()));
        
        client.setMotionHandler(motionId -> 
            System.out.println("Received motion command: " + motionId));
        
        client.setEmotionHandler(emotionId -> 
            System.out.println("Received emotion command: " + emotionId));

        if (!client.start()) {
            System.out.println("Failed to start client");
            return;
        }

        // Keep sending heartbeat messages
        try {
            while (true) {
                JSONObject heartbeat = new JSONObject()
                    .put("type", "heartbeat")
                    .put("timestamp", System.currentTimeMillis());
                
                client.sendMessage(heartbeat);
                Thread.sleep(5000);
            }
        } catch (InterruptedException e) {
            System.out.println("Client interrupted");
        } finally {
            client.stop();
        }
    }
}
