package com.tiwater.example;

import com.tiwater.ticos.TicosClient;
import org.json.JSONObject;

public class Main {
    public static void main(String[] args) {
        // Create a client instance
        TicosClient client = new TicosClient("localhost", 9999);
        
        // Set message handlers
        client.setMotionHandler(id -> System.out.println("Received motion message id: " + id));
        client.setEmotionHandler(id -> System.out.println("Received emotion message id: " + id));
        client.setMessageHandler(msg -> System.out.println("Received message: " + msg));

        // Connect to server with auto-reconnect enabled
        if (client.connect(true)) {
            System.out.println("Connected to server successfully");
            
            // Create and send a message with custom data
            JSONObject message = new JSONObject()
                .put("func", "motion")
                .put("id", "1")
                .put("data", new JSONObject()
                    .put("speed", 1.0)
                    .put("repeat", 3));
            
            if (client.sendMessage(message)) {
                System.out.println("Message sent successfully");
            } else {
                System.out.println("Failed to send message");
            }
            
            // Keep the main thread running to receive messages
            try {
                while (true) {
                    Thread.sleep(1000);
                }
            } catch (InterruptedException e) {
                System.out.println("Shutting down...");
                client.disconnect();
            }
        } else {
            System.out.println("Failed to connect to server");
        }
    }
}
