# Ticos Client Java SDK

A Java client SDK for communicating with Ticos Server.

## Installation

Add the following dependency to your project's `pom.xml`:

```xml
<dependency>
    <groupId>com.tiwater</groupId>
    <artifactId>ticos-client</artifactId>
    <version>0.1.1</version>
</dependency>
```

Or if you're using Gradle, add this to your `build.gradle`:

```groovy
implementation 'com.tiwater:ticos-client:0.1.1'
```

## Usage

Here's a simple example of how to use the Ticos Client:

```java
import com.tiwater.ticos.TicosClient;

public class Example {
    public static void main(String[] args) {
        // Create a client instance
        TicosClient client = new TicosClient("localhost", 9999);
        
        // Set message handler
        client.setMotionHandler(id -> {
            System.out.println("Received motion message id: " + id);
        });

        // Connect to server with auto-reconnect enabled
        if (client.connect(true)) {
            System.out.println("Connected to server successfully");
            
            // Send a test message
            if (client.sendMessage("test", "123")) {
                System.out.println("Message sent successfully");
            }
            
            // Keep the application running for a while
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            
            // Disconnect when done
            client.disconnect();
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

### Constructor

```java
TicosClient(String host, int port)
TicosClient(String host, int port, int reconnectInterval)
```

### Methods

- `setHandler(MessageHandler handler)`: Set the message handler for incoming messages
- `boolean connect(boolean autoReconnect)`: Connect to the server
- `void disconnect()`: Disconnect from the server
- `boolean sendMessage(String func, String id)`: Send a message to the server

### MessageHandler Interface

```java
public interface MessageHandler {
    void handleMessage(String func, String id);
}
```

## Error Handling

The SDK uses Java's built-in logging framework (`java.util.logging.Logger`) for error reporting and debugging. You can configure the logging level and handlers according to your needs.

## Requirements

- Java 8 or higher
- org.json library (automatically managed by Maven/Gradle)

## Thread Safety

All public methods in `TicosClient` are thread-safe. The client uses `ReentrantLock` for synchronization, ensuring safe concurrent access from multiple threads.

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
