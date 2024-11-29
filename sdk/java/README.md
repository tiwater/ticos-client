# Ticos Client Java SDK

A Java client SDK for communicating with Ticos Server.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags?q=java-*)

## Installation

Current Version: 0.1.5

Add the following dependency to your project's `pom.xml`:

```xml
<dependency>
    <groupId>com.tiwater</groupId>
    <artifactId>ticos-client</artifactId>
    <version>0.1.5</version>
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
        } else {
            System.out.println("Failed to connect to server");
        }
    }
}
```

## Features

- **Easy-to-use API**: Simple and intuitive interface for sending and receiving messages
- **Auto Reconnection**: Automatically reconnects to the server if the connection is lost
- **Thread Safety**: All operations are thread-safe
- **Configurable Settings**: Customize connection parameters and reconnection intervals
- **Message Handling**: Flexible message handling through callback interface

## API Reference

### TicosClient

#### Constructor

```java
TicosClient(String host, int port)
```

#### Methods

- `boolean connect(boolean autoReconnect)`
  - Connect to the server
  - Returns true if connection successful

- `void disconnect()`
  - Disconnect from the server

- `boolean sendMessage(JSONObject message)`
  - Send a message to the server
  - message: A JSONObject containing the message data
  - Returns true if message sent successfully

- `void setMessageHandler(MessageHandler handler)`
  - Set handler for general messages

- `void setMotionHandler(MotionHandler handler)`
  - Set handler for motion messages

- `void setEmotionHandler(EmotionHandler handler)`
  - Set handler for emotion messages

### Message Format

Messages should be JSONObjects with the following structure:

```json
{
    "func": "string",  // Function/message type (e.g., "motion", "emotion")
    "id": "string",    // Message identifier
    "data": {          // Optional additional data
        "key": "value"
    }
}
```

## Error Handling

The SDK uses Java's built-in logging framework (`java.util.logging.Logger`) for error reporting and debugging. You can configure the logging level and handlers according to your needs.

## Requirements

- Java 8 or higher
- org.json library (automatically managed by Maven/Gradle)

## Thread Safety

All public methods in `TicosClient` are thread-safe. The client uses `ReentrantLock` for synchronization, ensuring safe concurrent access from multiple threads.

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
