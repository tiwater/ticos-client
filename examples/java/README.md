# Ticos Client Java Example

This example demonstrates how to use the Ticos Client Java SDK to communicate with a Ticos server.

## Prerequisites

- Java 8 or higher
- Maven 3.6 or higher
- ticos-client 0.1.7

## Getting Started

1. Clone the repository:
```bash
git clone https://github.com/tiwater/ticos-client.git
cd ticos-client/examples/java
```

2. Build the project:
```bash
mvn clean package
```

3. Run the example:
```bash
mvn exec:java
```

## Code Explanation

The example demonstrates the following features of the Ticos Client SDK:

1. Creating a client instance:
```java
TicosClient client = new TicosClient(9999);
```

2. Setting up message handlers:
```java
// Generic message handler
client.setMessageHandler(message -> 
    System.out.println("Received message: " + message.toString()));

// Motion handler
client.setMotionHandler(motionId -> 
    System.out.println("Received motion command: " + motionId));

// Emotion handler
client.setEmotionHandler(emotionId -> 
    System.out.println("Received emotion command: " + emotionId));
```

3. Starting the client:
```java
if (!client.start()) {
    System.out.println("Failed to start client");
    return;
}
```

4. Sending heartbeat messages:
```java
JSONObject heartbeat = new JSONObject()
    .put("name", "heartbeat")
    .put("parameters", new JSONObject());
client.sendMessage(heartbeat);
```

5. Proper cleanup:
```java
client.stop();
```

## Features

- Client initialization and startup
- Message, motion, and emotion event handling
- Periodic heartbeat message sending
- Proper error handling and cleanup
- Graceful shutdown

## Error Handling

The example includes comprehensive error handling:
- Client startup failure handling
- Message sending error handling
- Proper resource cleanup on shutdown
- Interrupt handling for graceful termination

## Message Format

Messages use the following JSON format:

```json
{
    "name": "string",    // The message name (e.g., "motion", "emotion", "heartbeat")
    "parameters": {      // Parameters specific to the message type
        // message-specific parameters
    }
}
```

#### Motion Message Example

```json
{
    "name": "motion",
    "parameters": {
        "id": "1",
        "speed": 1.0,
        "repeat": 3
    }
}
```

#### Emotion Message Example

```json
{
    "name": "emotion",
    "parameters": {
        "id": "1",
        "intensity": 0.8,
        "duration": 2.5
    }
}
```

## Additional Resources

- [Ticos Client SDK Documentation](https://github.com/tiwater/ticos-client)
- [Maven Central Repository](https://central.sonatype.com/artifact/com.tiwater/ticos-client/0.1.7)

## License

This example is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.
