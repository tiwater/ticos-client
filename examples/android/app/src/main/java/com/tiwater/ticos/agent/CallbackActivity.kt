package com.tiwater.ticos.agent

import android.os.Bundle
import android.os.RemoteException
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject
import com.tiwater.ticos.common.ITicosMessageCallback
import com.tiwater.ticos.service.TicosAgentClient

/**
 * Callback 演示界面
 * 展示如何使用 Ticos Agent 的 Callback 功能
 */
class CallbackActivity : AppCompatActivity() {
    companion object {
        private const val TAG = "CallbackDemo"
    }

    private lateinit var client: TicosAgentClient
    private lateinit var statusTextView: TextView
    private lateinit var messageTextView: TextView
    private lateinit var motionTextView: TextView
    private lateinit var emotionTextView: TextView

    // 定义 Callback 消息回调
    private val messageCallback = object : ITicosMessageCallback.Stub() {
        override fun onMessage(message: String) {
            Log.d(TAG, "Received message: $message")
            runOnUiThread {
                try {
                    messageTextView.text = "消息: $message"
                } catch (e: Exception) {
                    Log.e(TAG, "Error updating UI", e)
                }
            }
        }

        override fun onMotion(parameters: String) {
            Log.d(TAG, "Received motion: $parameters")
            runOnUiThread {
                try {
                    motionTextView.text = "动作: $parameters"
                } catch (e: Exception) {
                    Log.e(TAG, "Error updating UI", e)
                }
            }
        }

        override fun onEmotion(parameters: String) {
            Log.d(TAG, "Received emotion: $parameters")
            runOnUiThread {
                try {
                    emotionTextView.text = "情绪: $parameters"
                } catch (e: Exception) {
                    Log.e(TAG, "Error updating UI", e)
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_callback_demo)

        // 初始化视图
        statusTextView = findViewById(R.id.statusTextView)
        messageTextView = findViewById(R.id.messageTextView)
        motionTextView = findViewById(R.id.motionTextView)
        emotionTextView = findViewById(R.id.emotionTextView)

        // 初始化客户端
        client = TicosAgentClient(this)

        // 绑定服务
        client.bindService { bound ->
            if (bound) {
                updateStatus("服务已连接")
                registerCallback()
            } else {
                updateStatus("服务未连接")
            }
        }

        // 设置按钮点击事件
        // findViewById<Button>(R.id.sendMessageButton).setOnClickListener {
        //     sendTestMessage()
        // }
    }

    private fun updateStatus(status: String) {
        runOnUiThread {
            statusTextView.text = "状态: $status"
        }
    }

    private fun registerCallback() {
        try {
            client.registerMessageCallback(messageCallback)
            updateStatus("已注册消息回调")
        } catch (e: RemoteException) {
            Log.e(TAG, "Error registering callback", e)
            updateStatus("注册回调失败: ${e.message}")
        }
    }

    private fun sendTestMessage() {
        Thread {
            try {
                val json = JSONObject().apply {
                    put("type", "test")
                    put("content", "Hello from Ticos Agent")
                }
                client.sendMessage(json.toString())
                runOnUiThread {
                    Toast.makeText(this@CallbackActivity, "消息已发送", Toast.LENGTH_SHORT).show()
                }
            } catch (e: RemoteException) {
                Log.e(TAG, "Failed to send Callback message", e)
                runOnUiThread {
                    Toast.makeText(this@CallbackActivity, "发送失败: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error sending message", e)
                runOnUiThread {
                    Toast.makeText(this@CallbackActivity, "发送错误: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }.start()
    }

    override fun onDestroy() {
        try {
            // 注销回调
            client.unregisterMessageCallback(messageCallback)
        } catch (e: Exception) {
            Log.e(TAG, "Error unregistering callback", e)
        }

        // 解绑服务
        client.unbindService()
        super.onDestroy()
    }
}
