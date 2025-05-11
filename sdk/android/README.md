<img src="https://cloud.ticos.ai/logo.svg" alt="Ticos Logo" width="80" height="auto">

# Ticos-Agent Android Client SDK User Guide

> **Prerequisites**: Make sure the Android SDK is installed.

## Integration Guide

### 1. Obtain the Development Package

Verify the latest versions of `ticos-agent-common` and `ticos-agent-service` from Maven, such as 0.9.0.

### 2. Add Dependencies

Edit the `build.gradle.kts` file of your application module to include the following dependencies (ensure version numbers are correct):

```gradle
dependencies {
    implementation("com.tiwater:ticos-agent-common:0.9.0")
    implementation("com.tiwater:ticos-agent-service:0.9.0")
    implementation("com.tiwater:ticos-client:0.1.9")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-core:1.6.3")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
}
```

Note: If the Ticos team provides AAR test packages directly, such as:

    `ticos-common-x.y.z.aar` and `ticos-service-x.y.z.aar`

    Place them in the `libs` directory of your Android project.

    Update dependencies in the `build.gradle.kts` file of your application module accordingly (ensure version numbers are correct):

```gradle
dependencies {
    implementation(files("libs/ticos-common-x.y.z.aar"))
    implementation(files("libs/ticos-service-x.y.z.aar"))
    
    implementation("com.tiwater:ticos-client:0.1.9")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-core:1.6.3")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
}
```

### 3. Set Permissions

Add service declarations and the following permissions to the application's `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-feature android:name="android.hardware.camera" android:required="false" />
<uses-feature android:name="android.hardware.camera.autofocus" />
```

> **Note**: The main application must ensure that `android.Manifest.permission.RECORD_AUDIO` and `android.Manifest.permission.CAMERA` permissions are granted upon startup.

### 4. Using TicosAgentClient

`TicosAgentClient` is the primary interface to access Ticos Agent services. It provides functionalities such as service binding, configuration management, and status monitoring.

#### 4.1 Core API

Below are some core methods:

| Method | Description |
|--------|-------------|
| `initialize(configSaveMode: ConfigSaveMode, debug: Boolean)` | Initialize service configuration. |
| `getServiceConfig()` | Get the current configuration (returns a TOML formatted string). |
| `updateServiceConfig(tomlConfig)` | Update configuration (TOML formatted string). |
| `startService()` | Start the service. Returns true if the start is successful. |
| `stopService()` | Stop the service. |
| `restartService()` | Restart the service. |
| `getServiceStatus()` | Get the service status (returns a description as a string). |
| `isServiceRunning()` | Check if the service is running (returns a boolean value). |
| `registerMessageCallback(callback)` | Register a message callback. |
| `unregisterMessageCallback(callback)` | Unregister a message callback. |
| `registerErrorCallback(callback)` | Register an error callback (GStreamer error notification). |
| `unregisterErrorCallback(callback)` | Unregister an error callback. |
| `isServiceBound()` | Check if the service is bound. |
| `bindService(callback)` | Bind the service (asynchronously). |
| `unbindService()` | Unbind the service. |

#### 4.2 Creating a Client Instance

Create an instance of `TicosAgentClient` within an `Activity` or `Fragment`:

```kotlin
val ticosClient = TicosAgentClient(context)
```

#### 4.3 Service Binding and Lifecycle Management

Bind and unbind the service (usually called in `onStart`/`onResume` and `onStop`/`onPause`):

```kotlin
// Bind the service
ticosClient.bindService { connected ->
    if (connected) {
        // Service connected successfully
    } else {
        // Service connection failed
    }
}

// Unbind the service
ticosClient.unbindService()
```

#### 4.4 Initializing the Service

Initialize after the service is successfully bound:

```kotlin
ticosClient.initialize(ConfigSaveMode.EXTERNAL_STORAGE, debugMode)
```

> **ConfigSaveMode** supports the following modes:
> - **PREFERENCE**: Configuration is saved in preferences.
> - **INTERNAL_STORAGE**: Configuration is saved as `config.toml` in internal storage.
> - **EXTERNAL_STORAGE**: Configuration is saved as `config.toml` on an external storage card.
Both storage modes save paths as sdcard/Android/<project_package>/files/config/config.toml (the exact path can vary slightly with different systems).

`debugMode` is used to control whether to output GStreamer logs (this should be set before `startService()`). Once `startService` is called, the process must be completely terminated to switch the debug mode again.

#### 4.5 Registering a Message Callback

Implement the message callback interface and register it:

```kotlin
val messageCallback = object : ITicosMessageCallback.Stub() {
    override fun onMessage(message: String) {
        Log.d(TAG, "Received message: $message")
        // Handle messages sent by the server
    }

    override fun onMotion(parameters: String) {
        Log.d(TAG, "Received motion: $parameters")
        // Handle motion events
    }

    override fun onEmotion(parameters: String) {
        Log.d(TAG, "Received emotion: $parameters")
        // Handle emotion events
    }
}

ticosClient.registerMessageCallback(messageCallback)
```

Unregister the callback:

```kotlin
ticosClient.unregisterMessageCallback(messageCallback)
```

#### 4.6 Registering an Error Callback

Implement the error callback interface and register it:

```kotlin
val errorCallback = object : ITicosErrorCallback.Stub() {
    override fun onError(message: String, code: Int) {
        // Error handling logic
        runOnUiThread {
            Toast.makeText(this@MainActivity, 
                "GStreamer Error: $message (Code: $code)", 
                Toast.LENGTH_LONG).show()
        }
    }
}

// Register callback (call after the service is successfully connected)
ticosClient.registerErrorCallback(errorCallback)

// Unregister callback (call in onStop)
ticosClient.unregisterErrorCallback(errorCallback)
```

#### 4.7 Starting/Stopping the Service

Start or stop the service as needed:

```kotlin
ticosClient.startService()
// Interactions can proceed after the service is started
...
ticosClient.stopService()
```

#### 4.8 A Simple Example

```kotlin
class MainActivity : AppCompatActivity() {
    private lateinit var ticosClient: TicosAgentClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ticosClient = TicosAgentClient(this)
    }

    override fun onStart() {
        super.onStart()
        ticosClient.bindService { connected ->
            if (connected) {
                val config = ticosClient.getServiceConfig()
                ticosClient.startService()
            }
        }
    }

    override fun onStop() {
        super.onStop()
        ticosClient.unbindService()
    }
}
```

Please refer to the [Android client demo](https://github.com/tiwater/ticos-client/blob/main/examples/android/README_zh.md).

### 4.9 Considerations

- Ensure you call other APIs after the service binding is successful (i.e., when the `bindService` callback returns `true`).
- Currently, only the `arm64-v8a` architecture is supported.

## License

Copyright 2023-2025 Tiwater Limited. All rights reserved.