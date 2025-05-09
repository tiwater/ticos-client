<img src="https://cloud.ticos.ai/logo.svg" alt="Ticos Logo" width="80" height="auto">

# Ticos-Agent Android Client SDK 说明

前提条件，已安装有 Android SDK。

## 集成指南

### 1. 获取开发包 

获取 Ticos Agent Android SDK 开发包 ticos-common-x.y.z.aar 和 ticos-service-x.y.z.aar。将他们放至 Android 项目 libs 目录下。


### 2. 添加依赖

在应用模块的 `build.gradle.kts` 中添加依赖，注意设置正确的版本号：

```gradle
dependencies {
    implementation(files("libs/ticos-common-x.y.z.aar"))
    implementation(files("libs/ticos-service-x.y.z.aar"))
    
    implementation("com.tiwater:ticos-client:0.1.9")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-core:1.6.3")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
}
```

### 3. 操作权限

在应用的 `AndroidManifest.xml` 中添加服务声明和所需权限：

```xml
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
    <uses-feature android:name="android.hardware.camera"  android:required="false" />
    <uses-feature android:name="android.hardware.camera.autofocus" />
```

主程序启动后应确保获得下列授权：
android.Manifest.permission.RECORD_AUDIO
android.Manifest.permission.CAMERA

### 4. TicosAgentClient 使用指南

`TicosAgentClient` 是访问 Ticos Agent 服务的主要客户端接口，封装了服务绑定、配置管理和状态监控等功能。

#### 4.1 核心API
| 方法 | 说明 |
|------|------|
| initializeconfigSaveMode: ConfigSaveMode, debug: Boolean | 初始化服务配置。 |
| getServiceConfig() | 获取当前配置(返回 TOML 格式的字符串) |
| updateServiceConfig(tomlConfig) | 更新配置( TOML 格式的字符串) |
| startService() | 启动服务 |
| stopService() | 停止服务 | 
| restartService() | 重启服务 |
| getServiceStatus() | 获取服务状态 |
| setPreviewSurface(surface) | 设置视频预览Surface |
| registerMessageCallback(callback) | 注册消息回调 |

#### 4.2 创建客户端

```kotlin
// 在Activity/Fragment中创建实例
val ticosClient = TicosAgentClient(context)
```

#### 4.3 服务绑定与生命周期管理

// 绑定服务（通常在onStart/resume时调用）
```kotlin
ticosClient.bindService { connected ->
    if (connected) {
        // 服务连接成功
    } else {
        // 服务连接失败
    }
}
```
// 解绑服务（通常在onStop/pause时调用） 
```kotlin
ticosClient.unbindService()
```

#### 4.4 初始化

// 初始化服务（在绑定成功后调用）
```kotlin
ticosClient.initialize(ConfigSaveMode.EXTERNAL_STORAGE, debugMode)
```
ConfigSaveMode 有3种模式：
    PREFERENCE,
    INTERNAL_STORAGE, 
    EXTERNAL_STORAGE
PREFERENCE 会将配置信息保存在 preference 中；
INTERNAL_STORAGE 会作为 config.toml 保存在内置内存卡；
EXTERNAL_STORAGE 会作为 config.toml 保存在外置存储卡中，如果外置存储卡不存在，则保存在内置存储卡中。
后两种形式的存储路径均为 sdcard/Android/<project_package>/files/config/config.toml (随系统不同，具体路径会略有差异)。

debugMode 控制是否输出 Gstreamer log。但此选项需在调用 startService() 前设置。一旦 startService 调用后，需要彻底终止进程，才能重新切换调试状态。

#### 4.4 消息回调处理
实现消息回调接口：
```kotlin
val messageCallback = object : ITicosMessageCallback.Stub() {
    override fun onMessage(message: String) {
        Log.d(TAG, "Received message: $message")
        runOnUiThread {
            // 处理服务端推送的消息
        }
    }

    override fun onMotion(parameters: String) {
        Log.d(TAG, "Received motion: $parameters")
        runOnUiThread {
            // 处理服务端推送的消息
        }
    }

    override fun onEmotion(parameters: String) {
        Log.d(TAG, "Received emotion: $parameters")
        runOnUiThread {
            // 处理服务端推送的消息
        }
    }
}
```
注册/注销回调：
```kotlin
// 注册回调
ticosClient.registerMessageCallback(callback)

// 注销回调
ticosClient.unregisterMessageCallback(callback)
```

#### 4.5 启动/停止服务
根据需要，启动或停止 ticos agent 服务：
```kotlin
ticosClient.startService()
// 服务启动后即可以与终端进行交互
...
ticosClient.stopService()
```

#### 4.6 完整示例
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
                // 获取当前配置
                val config = ticosClient.getServiceConfig()
                // 启动服务
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

#### 4.7 注意事项

* 所有API调用应在服务绑定成功后进行（bindService回调返回true）
* 配置更新是异步操作，建议通过消息回调监听状态变化
* 目前仅提供 arm64-v8a 架构支持