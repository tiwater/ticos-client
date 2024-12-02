# Ticos Client SDK

Ticos Client SDK provides a simple and efficient way to communicate with Ticos Server. It allows you to create client applications that can send and receive messages, handle motion and emotion commands, and maintain a heartbeat connection with the server.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags)

## Project Structure

```
ticos-client/
├── sdk/
│   ├── java/          # Java SDK implementation
│   └── python/        # Python SDK implementation
├── examples/
│   ├── java/          # Java client examples
│   └── python/        # Python client examples
└── .github/
    └── workflows/     # GitHub Actions workflow definitions
```

## Available SDKs

### Java SDK

- Maven dependency:
  ```xml
  <dependency>
      <groupId>com.tiwater</groupId>
      <artifactId>ticos-client</artifactId>
      <version>0.1.5</version>
  </dependency>
  ```
- [Java SDK Documentation](sdk/java/README.md)
- [Java Example](examples/java/README.md)

### Python SDK

- PyPI package:
  ```bash
  pip install ticos-client==0.1.5
  ```
- [Python SDK Documentation](sdk/python/README.md)
- [Python Example](examples/python/README.md)

## Quick Start

Both Java and Python SDKs follow a similar pattern for creating a client:

1. Create a TicosClient instance with a specific port
2. Set up message, motion, and emotion handlers
3. Start the client
4. Send messages (like heartbeats) as needed
5. Handle cleanup when done

Check the examples directory for complete working implementations in both Java and Python.

## Development

1. Clone the repository:
   ```bash
   git clone https://github.com/tiwater/ticos-client.git
   cd ticos-client
   ```

2. Choose your preferred SDK:
   - [Java Development Guide](sdk/java/README.md)
   - [Python Development Guide](sdk/python/README.md)

## Release Process

We use GitHub Actions to automate our release process. Here's how to trigger different versions of releases:

### Release Commands

```bash
# Create and push a Java release tag
git tag java-v0.1.1
git push origin java-v0.1.1

# Create and push a Python release tag
git tag python-v0.1.1
git push origin python-v0.1.1
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
