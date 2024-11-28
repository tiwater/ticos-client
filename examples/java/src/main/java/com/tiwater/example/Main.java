package com.tiwater.example;

import com.tiwater.ticos.TicosClient;
import org.json.JSONObject;

public class Main {
    public static void main(String[] args) {
        // Create a client instance
        TicosClient client = new TicosClient("localhost", 9999);
        
        // Set message handlers
        client.setMessageHandler(message -> {
            System.out.println("Received message: " + message.toString());
        });

        client.setMotionHandler(id -> {
            System.out.println("Received motion message id: " + id);
        });

        client.setEmotionHandler(id -> {
            System.out.println("Received emotion message id: " + id);
        });

        // Connect to server with auto-reconnect enabled
        if (client.connect(true)) {
            System.out.println("Connected to server successfully");
            
            // Send a test message
            if (client.sendMessage("test", "123")) {
                System.out.println("Message sent successfully");
            } else {
                System.out.println("Failed to send message");
            }
            
            // Keep the main thread running for a while to receive messages
            try {
                Thread.sleep(5000);  // 5 seconds
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            
            // Disconnect when done
            client.disconnect();
        } else {
            System.out.println("Failed to connect to server");
        }
    }
}
