package com.tiwater.example;

import com.tiwater.ticos.TicosClient;
import com.tiwater.ticos.storage.SQLiteStorageService;
import org.json.JSONObject;
import java.util.Random;
import java.util.logging.Logger;
import java.text.SimpleDateFormat;
import java.util.Date;
import com.tiwater.ticos.SaveMode;

public class Main {
    private static final Logger LOGGER = Logger.getLogger(Main.class.getName());
    private static final Random random = new Random();

    public static void main(String[] args) {
        // Create and start the client with internal save mode
        TicosClient client = new TicosClient(9999, SaveMode.INTERNAL);
        
        client.enableLocalStorage(new SQLiteStorageService());
        // Set message handlers
        client.setMessageHandler(message -> 
            LOGGER.info("Received message: " + message.toString()));
            
        client.setMotionHandler(parameters -> 
            LOGGER.info("Received motion command with parameters: " + parameters.toString()));
            
        client.setEmotionHandler(parameters -> 
            LOGGER.info("Received emotion command with parameters: " + parameters.toString()));

        client.start();

        try {
            // Keep the main thread running and send test messages
            SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
            while (true) {
                // Send test message every 10 seconds
                Thread.sleep(10000);
                
                JSONObject testMessage = new JSONObject();
                testMessage.put("name", "test");
                JSONObject messageArgs = new JSONObject();
                messageArgs.put("timestamp", dateFormat.format(new Date()));
                messageArgs.put("random_value", random.nextInt(100) + 1);
                testMessage.put("arguments", messageArgs);
                
                if (client.sendMessage(testMessage)) {
                    LOGGER.info("Sent test message: " + testMessage.toString());
                } else {
                    LOGGER.warning("Failed to send test message");
                }
            }
        } catch (InterruptedException e) {
            LOGGER.info("Client interrupted");
        } finally {
            client.stop();
        }
    }
}
