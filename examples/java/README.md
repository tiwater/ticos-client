# Ticos Client Java Example

This example demonstrates how to use the Ticos Client Java SDK to communicate with a Ticos server.

## Prerequisites

- Java 8 or higher
- Maven 3.6 or higher
- A running Ticos server (default: localhost:9999)

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
TicosClient client = new TicosClient("localhost", 9999);
```

2. Setting up message handlers:
```java
// Generic message handler
client.setMessageHandler(message -> {
    System.out.println("Received message: " + message.toString());
});

// Motion-specific handler
client.setMotionHandler(id -> {
    System.out.println("Received motion message id: " + id);
});

// Emotion-specific handler
client.setEmotionHandler(id -> {
    System.out.println("Received emotion message id: " + id);
});
```

3. Connecting to the server with auto-reconnect:
```java
client.connect(true);
```

4. Sending messages:
```java
client.sendMessage("test", "123");
```

5. Proper cleanup:
```java
client.disconnect();
```

## Configuration

The example connects to `localhost:9999` by default. To connect to a different server:

1. Modify the host and port in `Main.java`:
```java
TicosClient client = new TicosClient("your-server-host", your-server-port);
```

2. Rebuild and run the project.

## Error Handling

The example includes basic error handling:
- Connection failure handling
- Message sending failure handling
- Proper resource cleanup

## Additional Resources

- [Ticos Client SDK Documentation](https://github.com/tiwater/ticos-client)
- [Maven Central Repository](https://central.sonatype.com/artifact/com.tiwater/ticos-client/0.1.0)

## License

This example is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.
