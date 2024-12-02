# Ticos Client Java SDK

A Java client SDK for communicating with Ticos Server. This client SDK allows you to create applications that can send messages, handle motion and emotion commands, and maintain a heartbeat connection with the server.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags?q=java-*)

## Installation

Add the following dependency to your project's `pom.xml`:

```xml
<dependency>
    <groupId>com.tiwater</groupId>
    <artifactId>ticos-client</artifactId>
    <version>0.1.6</version>
</dependency>
```

Or if you're using Gradle, add this to your `build.gradle`:

```groovy
implementation 'com.tiwater:ticos-client:0.1.5'
```

## Usage

Here's a simple example of how to use the Ticos Client:

```java
import com.tiwater.ticos.TicosClient;
import org.json.JSONObject;

public class Example {
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

        // Start the client
        if (!client.start()) {
            System.out.println("Failed to start client");
            return;
        }

        try {
            // Example: Send a heartbeat message
            JSONObject heartbeat = new JSONObject()
                .put("type", "heartbeat")
                .put("timestamp", System.currentTimeMillis());
            
            client.sendMessage(heartbeat);
            
            // Keep the main thread running
            while (true) {
                Thread.sleep(1000);
            }
        } catch (InterruptedException e) {
            System.out.println("Client interrupted");
        } finally {
            client.stop();
        }
    }
}
```

## Features

- Simple and intuitive API for sending and receiving messages
- Automatic handling of connection management
- Thread-safe operations
- Support for different message types (general messages, motion commands, emotion commands)
- Built-in heartbeat mechanism
- Proper resource cleanup

## API Reference

### TicosClient

#### Constructor

```java
TicosClient(int port)
```

Creates a new Ticos client instance.

#### Methods

- `boolean start()`
  - Start the client
  - Returns true if startup successful

- `void stop()`
  - Stop the client and clean up resources

- `boolean sendMessage(JSONObject message)`
  - Send a message to the server
  - message: A JSONObject containing the message data
  - Returns true if message sent successfully

- `void setMessageHandler(MessageHandler handler)`
  - Set handler for general messages
  - handler: Lambda or class implementing MessageHandler interface

- `void setMotionHandler(MotionHandler handler)`
  - Set handler for motion commands
  - handler: Lambda or class implementing MotionHandler interface

- `void setEmotionHandler(EmotionHandler handler)`
  - Set handler for emotion commands
  - handler: Lambda or class implementing EmotionHandler interface

### Message Format

Messages should be JSONObjects with the following structure:

```json
{
    "type": "string",    // Message type (e.g., "heartbeat", "motion", "emotion")
    "timestamp": "long", // Optional timestamp
    "data": {}          // Optional additional data
}
```

## Thread Safety

All operations in TicosClient are thread-safe. The client handles message sending and receiving in separate threads, making it safe to use in multi-threaded applications.

## Error Handling

The client includes comprehensive error handling:
- Startup failure detection
- Message sending error handling
- Proper resource cleanup on shutdown
- Thread interruption handling

For more examples, check out the [examples/java](../../examples/java) directory.

## Requirements

- Java 8 or higher
- org.json library (automatically managed by Maven/Gradle)

## Development

1. Clone the repository
2. Build the project:
   ```bash
   mvn clean install
   ```
3. Run tests:
   ```bash
   mvn test
   ```

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
