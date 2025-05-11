<img src="https://cloud.ticos.ai/logo.svg" alt="Ticos Logo" width="80" height="auto">

# Ticos Agent Client Demo

## Overview

The Ticos Agent Client Demo is a simple Android application designed to demonstrate how to interact with the Ticos Agent service as a third-party client. With this demo application, users can perform the following actions:

- Connect to the Ticos Agent service
- Start and stop the Ticos Agent service
- Retrieve and update the configuration of the Ticos Agent

This application illustrates how to integrate with the Ticos Agent service, providing developers with a reference example for integrating Ticos Agent into other applications.

## System Requirements

- Android 5.0 (API level 21) or higher
- Supports arm64-v8a architecture
- Android SDK and JDK must be installed in the development environment

## Installation Instructions

### Build from Source

1. Clone the demo code to your local machine:
   ```bash
   git clone https://github.com/tiwater/ticos-client.git
   cd ticos-client/examples/android
   ```

2. Set up the Android SDK environment variable:
   ```bash
   export ANDROID_HOME=/Path_to_Android_sdk
   ```

3. Build the demo application:
   
   ```bash
   ./gradlew assembleDebug
   ```

4. Install the application:
   Connect a USB cable between the development computer and the OTG port of the Android device, then run:
   ```bash
   ./gradlew installDebug
   ```
   This will install the demo application on the target device for testing.

## User Guide

### Basic Configuration

1. In the settings interface, complete the following basic configurations:

   - `agent_id`
   - `secret_key` (API key)

2. If a camera is available and you wish to enable visual features, enable the following options:

   - Enable Camera
   - Enable Camera Upload

3. Configure other options as needed.

4. At the bottom of the settings interface, you can import/export the configuration file, or directly edit the raw TOML format configuration.

5. You can also copy the configuration file directly, which is located in: `sdcard/Android/<project_package>/files/config/config.toml`. For more details, refer to the [SDK documentation](https://github.com/tiwater/ticos-client/sdk/android/README.md).

### Trial

Return to the main interface and click the "Start" button to initiate a conversation with the agent.

- Note: The "Debug Mode" toggle controls whether to output the Gstreamer log. This option must be set before the service starts. Once the service has started, this toggle is disabled. You need to completely kill the process to change the debug state again.

### Callback Testing

Click the callback demo button to see real-time information if there are any actions.

## License

Copyright © 2023-2025 Tiwater Limited. All rights reserved.