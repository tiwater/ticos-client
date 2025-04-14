# Ticos Client Java SDK

A Java client SDK for communicating with Ticos Server. This client SDK allows you to create applications that can send messages, handle motion and emotion commands, and maintain a heartbeat connection with the server.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags?q=java-*)

## Installation

Add the following dependency to your project's `pom.xml`:

```xml
<dependency>
    <groupId>com.tiwater</groupId>
    <artifactId>ticos-client</artifactId>
    <version>0.1.8</version>
</dependency>
```

Or if you're using Gradle, add this to your `build.gradle`:

```groovy
implementation 'com.tiwater:ticos-client:0.1.8'
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
            
        client.setMotionHandler(parameters -> 
            System.out.println("Received motion command with parameters: " + parameters.toString()));
            
        client.setEmotionHandler(parameters -> 
            System.out.println("Received emotion command with parameters: " + parameters.toString()));

        // Start the client
        if (!client.start()) {
            System.out.println("Failed to start client");
            return;
        }

        try {

            // Example: Send a motion command
            JSONObject motion = new JSONObject()
                .put("name", "motion")
                .put("arguments", new JSONObject()
                    .put("motion_tag", "hug")
                    .put("speed", 1.0)
                    .put("repeat", 3));
            
            client.sendMessage(motion);

            // Example: Send an emotion command
            JSONObject emotion = new JSONObject()
                .put("name", "emotion")
                .put("arguments", new JSONObject()
                    .put("emotion_tag", "smile")
                    .put("intensity", 0.8)
                    .put("duration", 2.5));
            
            client.sendMessage(emotion);
            
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
  - handler: Function that takes a JSONObject message as parameter

- `void setMotionHandler(MotionHandler handler)`
  - Set handler for motion commands
  - handler: Function that takes a JSONObject parameters as parameter

- `void setEmotionHandler(EmotionHandler handler)`
  - Set handler for emotion commands
  - handler: Function that takes a JSONObject parameters as parameter

### Message Format

Messages should be JSONObjects with the following structure:

```json
{
    "name": "string",    // The name of the message (e.g., "motion", "emotion", "heartbeat")
    "arguments": {      // A JSON object of parameters specific to the message type
        // message-specific parameters
    }
}
```

#### Motion Message Arguments

The contents of the "arguments" object for a ticos message should be a JSON object, the exact structure of which depends on the requirement of your application.

For example, the following JSON object is a valid motion message:
```json
{
    "motion_tag": "string",     // The motion ID
    "speed": 1.0,       // Motion speed (optional, default: 1.0)
    "repeat": 1         // Number of times to repeat (optional, default: 1)
}
```

#### Emotion Message Arguments

The contents of the "arguments" object for a ticos message should be a JSON object, the exact structure of which depends on the requirement of your application.

For example, the following JSON object is a valid motion message:
```json
{
    "emotion_tag": "string",     // The emotion ID
    "intensity": 1.0,   // Emotion intensity (optional, default: 1.0)
    "duration": 2.5     // Duration in seconds (optional)
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
