<img src="https://cloud.ticos.ai/logo.svg" alt="Ticos Logo" width="80" height="auto">

# Ticos Agent Client Demo

## 概述

Ticos Agent Client Demo 是一个简单的 Android 应用程序，用于演示如何作为第三方客户端与 Ticos Agent 服务进行交互。通过这个演示应用，用户可以执行以下操作：

- 连接到 Ticos Agent 服务
- 启动和停止 Ticos Agent 服务
- 获取和更新 Ticos Agent 的配置

这个应用程序展示了如何与 Ticos Agent 服务进行集成，为开发者提供了一个集成 Ticos Agent 到其他应用的参考示例。

## 系统要求

- Android 5.0 (API level 21) 或更高版本
- 支持 arm64-v8a 架构
- 开发环境已安装有 Android SDK 及 JDK

## 安装方法

### 从源码构建

1. 克隆本示例代码到本地：
   ```bash
   git clone https://github.com/tiwater/ticos-client.git
   cd ticos-client/examples/android
   ```

2. 配置 Android SDK 环境变量：
   ```bash
   export ANDROID_HOME=/Path_to_Android_sdk
   ```

3. 然后构建示例应用：

   ```bash
   ./gradlew assembleDebug
   ```

1. 安装应用：
   将 usb 线将开发电脑和 Android 设备的 OTG 端口连接，然后执行：
   ```bash
   ./gradlew installDebug
   ```
   即可在目标设备上安装测试本示例

## 使用指南

### 基础配置

1. 点击设置界面，完成以下基础项的配置：

* agent_id
* secret_key （API 密钥）

2. 如果有摄像头，想启用视觉功能，请使能下面两项：

* 启用摄像头
* 启用摄像头上传

3. 根据需要配置其他选项

4. 设置界面最下方可以导入/导出配置文件，也可以直接编辑原始 TOML 格式的配置

5. 你也可以直接拷贝配置文件，默认在 SDCARD 下 sdcard/Android/<project_package>/files/config/config.toml。详细说明参见 [SDK 文档](https://github.com/tiwater/ticos-client/sdk/andoid/README_zh.md)

### 试用

返回主界面，点击“启动”按钮，即可启动与智能体对话。

* 注意：“调试模式”开关控制是否输出 Gstreamer log。但此选项需在启动服务之前设置。一旦启动服务后，此开关就失效，需要彻底杀死进程，才能重新切换调试状态。

### 回调测试

点击回调演示，如果有动作等信息会送，可以实时看见。

## 许可证

Copyright © 2023-2025 Tiwater Limited. All rights reserved.