<img src="https://cloud.ticos.ai/logo.svg" alt="Ticos Logo" width="80" height="auto">

# Ticos-Agent Android Client SDK 使用说明

> **前提条件**：确保已安装 Android SDK。

## 集成指南

### 1. 获取开发包

从 Maven 确认 ticos-agent-common 和 ticos-agent-service 的最新版本，例如 0.9.0。

### 2. 添加依赖

编辑应用模块的 `build.gradle.kts` 文件，增加以下依赖（请确认版本号正确）：

```gradle
dependencies {
    implementation("com.tiwater:ticos-agent-common:0.9.0")
    implementation("com.tiwater:ticos-agent-service:0.9.0")
    implementation("com.tiwater:ticos-client:0.1.9")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-core:1.6.3")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
}
```

注：如果 Ticos 团队直接获取的 aar 测试包，例如：

    `ticos-common-x.y.z.aar` 和 `ticos-service-x.y.z.aar`

    则将它们放置在您的 Android 项目 `libs` 目录中。

    应用模块的 `build.gradle.kts` 文件相应依赖改为（请确认版本号正确）：

```gradle
dependencies {
    implementation(files("libs/ticos-common-x.y.z.aar"))
    implementation(files("libs/ticos-service-x.y.z.aar"))
    
    implementation("com.tiwater:ticos-client:0.1.9")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-core:1.6.3")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
}
```

### 3. 设置权限

在应用的 `AndroidManifest.xml` 中，添加服务声明和以下权限：

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

> **注意**：主程序启动后应确保获得 `android.Manifest.permission.RECORD_AUDIO` 和 `android.Manifest.permission.CAMERA` 权限。

### 4. 使用 TicosAgentClient

`TicosAgentClient` 是访问 Ticos Agent 服务的主要接口。它提供了服务绑定、配置管理和状态监控等功能。

#### 4.1 核心API

以下是一些核心方法：

| 方法 | 说明 |
|------|------|
| `initialize(configSaveMode: ConfigSaveMode, debug: Boolean)` | 初始化服务配置。 |
| `getServiceConfig()` | 获取当前配置（返回 TOML 格式的字符串）。 |
| `updateServiceConfig(tomlConfig)` | 更新配置（TOML 格式的字符串）。 |
| `startService()` | 启动服务。启动成功返回 true |
| `stopService()` | 停止服务。 |
| `restartService()` | 重启服务。 |
| `getServiceStatus()` | 获取服务状态（返回字符串描述）。 |
| `isServiceRunning()` | 检查服务是否正在运行（返回布尔值）。 |
| `registerMessageCallback(callback)` | 注册消息回调。 |
| `unregisterMessageCallback(callback)` | 注销消息回调。 |
| `registerErrorCallback(callback)` | 注册错误回调（GStreamer错误通知）。 |
| `unregisterErrorCallback(callback)` | 注销错误回调。 |
| `isServiceBound()` | 检查服务是否已绑定。 |
| `bindService(callback)` | 绑定服务（异步）。 |
| `unbindService()` | 解绑服务。 |

#### 4.2 创建客户端实例

在 `Activity` 或 `Fragment` 中创建 `TicosAgentClient` 实例：

```kotlin
val ticosClient = TicosAgentClient(context)
```

#### 4.3 服务绑定与生命周期管理

绑定和解绑服务（通常在 `onStart`/`onResume` 和 `onStop`/`onPause` 中调用）：

```kotlin
// 绑定服务
ticosClient.bindService { connected ->
    if (connected) {
        // 服务连接成功
    } else {
        // 服务连接失败
    }
}

// 解绑服务
ticosClient.unbindService()
```

#### 4.4 初始化服务

在服务绑定成功后初始化：

```kotlin
ticosClient.initialize(ConfigSaveMode.EXTERNAL_STORAGE, debugMode)
```

> **ConfigSaveMode** 支持以下模式：
> - **PREFERENCE**: 配置保存在 preference 中。
> - **INTERNAL_STORAGE**: 配置作为 `config.toml` 保存在内置存储中。
> - **EXTERNAL_STORAGE**: 配置作为 `config.toml` 保存在外置存储卡中。
后两种形式的存储路径均为 sdcard/Android/<project_package>/files/config/config.toml (随系统不同，具体路径会略有差异)。

`debugMode` 用于控制是否输出 Gstreamer 日志（需在 `startService()` 前设置）。一旦 startService 调用后，需要彻底终止进程，才能重新切换调试状态。

#### 4.5 注册消息回调

实现消息回调接口并注册：

```kotlin
val messageCallback = object : ITicosMessageCallback.Stub() {
    override fun onMessage(message: String) {
        Log.d(TAG, "Received message: $message")
        // 处理服务端发送的消息
    }

    override fun onMotion(parameters: String) {
        Log.d(TAG, "Received motion: $parameters")
        // 处理运动事件
    }

    override fun onEmotion(parameters: String) {
        Log.d(TAG, "Received emotion: $parameters")
        // 处理情绪事件
    }
}

ticosClient.registerMessageCallback(messageCallback)
```

注销回调：

```kotlin
ticosClient.unregisterMessageCallback(messageCallback)
```

#### 4.6 注册错误回调

实现错误回调接口并注册：

```kotlin
val errorCallback = object : ITicosErrorCallback.Stub() {
    override fun onError(message: String, code: Int) {
        // 错误处理逻辑
        runOnUiThread {
            Toast.makeText(this@MainActivity, 
                "GStreamer Error: $message (Code: $code)", 
                Toast.LENGTH_LONG).show()
        }
    }
}

// 注册回调（在服务连接成功后调用）
ticosClient.registerErrorCallback(errorCallback)

// 注销回调（在onStop中调用）
ticosClient.unregisterErrorCallback(errorCallback)
```

#### 4.7 启动/停止服务

根据需要启动或停止服务：

```kotlin
ticosClient.startService()
// 服务启动后即可交互
...
ticosClient.stopService()
```

#### 4.8 完整示例

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

请参阅 [Android client demo](https://github.com/tiwater/ticos-client/blob/main/examples/android/README_zh.md)。

### 4.9 注意事项

- 确保在服务绑定成功后（即 `bindService` 回调返回 `true` 时）再调用其他 API。
- 当前仅提供 `arm64-v8a` 架构支持。

## 许可证

Copyright 2023-2025 Tiwater Limited. All rights reserved.