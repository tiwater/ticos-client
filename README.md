# Ticos Client SDK

Ticos Client SDK provides a simple and efficient way to communicate with Ticos Server. The SDK is available in multiple languages including Java and Python.

> **Note**: Check the latest SDK version at [GitHub Releases](https://github.com/tiwater/ticos-client/tags)

## Project Structure

```
ticos-client/
├── sdk/
│   ├── java/          # Java SDK implementation
│   └── python/        # Python SDK implementation
├── examples/
│   ├── java/          # Java usage examples
│   └── python/        # Python usage examples
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
