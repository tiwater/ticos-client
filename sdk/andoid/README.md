<img src="https://cloud.ticos.ai/logo.svg" alt="Ticos Logo" width="80" height="auto">

# Ticos-Agent Android Client SDK User Guide

> **Prerequisite**: Ensure Android SDK is installed.

## Integration Guide

### 1. Obtain SDK Packages

Get the Android SDK packages from Ticos team: `ticos-common-x.y.z.aar` and `ticos-service-x.y.z.aar`, and place them in your Android project's `libs` directory.

### 2. Add Dependencies

Edit the `build.gradle.kts` file of your application module and add the following dependencies (make sure the version numbers are correct):

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

In the `AndroidManifest.xml` of your application, add service declarations and the following permissions:

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

> **Note**: Ensure `android.Manifest.permission.RECORD_AUDIO` and `android.Manifest.permission.CAMERA` permissions are granted after launching the main application.

### 4. Use TicosAgentClient

`TicosAgentClient` is the primary interface for accessing the Ticos Agent service. It offers functions for service binding, configuration management, and status monitoring.

#### 4.1 Core API

Below are some core methods:

| Method | Description |
|--------|-------------|
| `initialize(configSaveMode: ConfigSaveMode, debug: Boolean)` | Initialize service configuration. |
| `getServiceConfig()` | Retrieve the current configuration (returns a string in TOML format). |
| `updateServiceConfig(tomlConfig)` | Update configuration (in TOML format). |
| `startService()` | Start the service. |
| `stopService()` | Stop the service. |
| `restartService()` | Restart the service. |
| `getServiceStatus()` | Get the service status. |
| `setPreviewSurface(surface)` | Set the video preview surface. |
| `registerMessageCallback(callback)` | Register a message callback. |

#### 4.2 Create Client Instance

Create an instance of `TicosAgentClient` in `Activity` or `Fragment`:

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

#### 4.4 Initialize Service

Initialize after the service has bound successfully:

```kotlin
ticosClient.initialize(ConfigSaveMode.EXTERNAL_STORAGE, debugMode)
```

> **ConfigSaveMode** supports the following modes:
> - **PREFERENCE**: Configuration is saved in preferences.
> - **INTERNAL_STORAGE**: Configuration is saved as `config.toml` in internal storage.
> - **EXTERNAL_STORAGE**: Configuration is saved as `config.toml` on an external storage card.
Both storage paths used in the latter two modes are sdcard/Android/<project_package>/files/config/config.toml (the exact path may vary slightly depending on the system).

`debugMode` controls whether to output Gstreamer logs (set before `startService()`). Once `startService` is called, you must terminate the process completely to switch debug states again.

#### 4.5 Register Message Callback

Implement the message callback interface and register it:

```kotlin
val messageCallback = object : ITicosMessageCallback.Stub() {
    override fun onMessage(message: String) {
        Log.d(TAG, "Received message: $message")
        // Handle messages sent from the server
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

#### 4.6 Start/Stop the Service

Start or stop the service as needed:

```kotlin
ticosClient.startService()
// Interact with the service once started
...
ticosClient.stopService()
```

#### 4.7 Complete Example

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

### 4.8 Notes

- Ensure APIs are called only after the service has been successfully bound (i.e., when the `bindService` callback returns `true`).
- Currently, only the `arm64-v8a` architecture is supported.

## License

Copyright © 2023-2025 Tiwater Limited. All rights reserved.