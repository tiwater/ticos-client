package com.tiwater.ticos.agent

import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.view.Menu
import android.view.MenuItem
import android.view.Surface
import android.view.SurfaceHolder
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import android.content.Intent
import android.os.Build
import android.os.Environment
import android.os.PowerManager
import android.provider.Settings
import android.net.Uri
import com.tiwater.ticos.agent.databinding.ActivityMainBinding
import com.tiwater.ticos.common.ConfigConstants
import com.tiwater.ticos.common.ConfigSaveMode
import com.tiwater.ticos.service.TicosAgentClient
import com.google.android.material.button.MaterialButton
import java.io.File

/**
 * MainActivity是Ticos Agent应用的主界面
 * 提供服务状态显示和控制功能
 */
class MainActivity : AppCompatActivity() {
    companion object {
        private const val TAG = "MainActivity"
    }
    
    private lateinit var binding: ActivityMainBinding
    private lateinit var ticosClient: TicosAgentClient
    private var previewSurface: Surface? = null
    private var debugMode = false  // 默认不启用调试模式
    private val permissionQueue = mutableListOf<String>()
    private var currentPermissionRequestCode = 0
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // 初始化 Ticos 客户端
        ticosClient = TicosAgentClient(this)
        
        // 设置按钮点击事件
        setupButtons()
        
        // 设置预览窗口
        setupPreviewSurface()
        
        // 绑定服务
        bindService()

        // 检查电池优化设置
        checkBatteryOptimization()
        
        // 初始化权限请求队列
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            // Android 10以下需要请求WRITE_EXTERNAL_STORAGE权限
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED) {
                permissionQueue.add(android.Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
        }
        
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            permissionQueue.add(android.Manifest.permission.RECORD_AUDIO)
        }
        
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED) {
            permissionQueue.add(android.Manifest.permission.CAMERA)
        }
        
        // 开始权限请求流程
        requestNextPermission()
    }
    
    private fun requestNextPermission() {
        if (permissionQueue.isNotEmpty()) {
            val permission = permissionQueue.removeAt(0)
            currentPermissionRequestCode = when (permission) {
                android.Manifest.permission.RECORD_AUDIO -> 1
                android.Manifest.permission.CAMERA -> 2
                android.Manifest.permission.WRITE_EXTERNAL_STORAGE -> 3
                else -> 0
            }
            ActivityCompat.requestPermissions(this, arrayOf(permission), currentPermissionRequestCode)
        }
    }
    
    override fun onStart() {
        super.onStart()
        if (!ticosClient.isServiceBound()) {
            bindService()
        }
        updateServiceStatus()
    }
    
    override fun onStop() {
        super.onStop()
        ticosClient.unbindService()
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                startActivity(Intent(this, SettingsActivity::class.java))
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    private fun setupButtons() {
        // 启动按钮
        binding.startButton.setOnClickListener {
            startService()
        }
        
        // 停止按钮
        binding.stopButton.setOnClickListener {
            stopService()
        }
        
        // 重启按钮
        binding.restartButton.setOnClickListener {
            restartService()
        }
        
        // 设置按钮
        binding.settingsButton.setOnClickListener {
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }
        
        // 调试模式开关
        binding.debugSwitch.setOnCheckedChangeListener { _, isChecked ->
            debugMode = isChecked
            Log.d(TAG, "Debug mode ${if (isChecked) "enabled" else "disabled"}")
            
            // 切换调试模式时重新初始化服务
            if (ticosClient.isServiceBound()) {
                initializeService()
            }
        }
        
        // WebSocket演示按钮点击事件
        binding.websocketButton.setOnClickListener {
            val intent = Intent(this, CallbackActivity::class.java)
            startActivity(intent)
        }
    }
    
    private fun setupPreviewSurface() {
        // binding.previewSurface.holder.addCallback(object : SurfaceHolder.Callback {
        //     override fun surfaceCreated(holder: SurfaceHolder) {
        //         previewSurface = holder.surface
        //         ticosClient.setPreviewSurface(previewSurface)
        //     }

        //     override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        //         // 不需要处理
        //     }

        //     override fun surfaceDestroyed(holder: SurfaceHolder) {
        //         previewSurface = null
        //         ticosClient.setPreviewSurface(null)
        //     }
        // })
    }
    
    private fun bindService() {
        ticosClient.bindService { connected ->
            if (connected) {
                Log.d(TAG, "Service connected")
                updateServiceStatus()
                previewSurface?.let { ticosClient.setPreviewSurface(it) }
                
                // 服务绑定成功后，初始化服务
                initializeService()
            } else {
                Log.d(TAG, "Service disconnected")
                updateServiceStatus()
            }
        }
    }
    
    private fun initializeService() {
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    ticosClient.initialize(ConfigSaveMode.EXTERNAL_STORAGE, debugMode)
                }
                Log.d(TAG, "Service initialized with configSaveMode: EXTERNAL_STORAGE, debug: $debugMode")
            } catch (e: Exception) {
                Log.e(TAG, "Error initializing service", e)
            }
        }
    }
    
    private fun startService() {
        lifecycleScope.launch {
            try {
                // 先初始化服务
                withContext(Dispatchers.IO) {
                    ticosClient.initialize(ConfigSaveMode.EXTERNAL_STORAGE, debugMode)
                }
                
                // 然后启动服务
                withContext(Dispatchers.IO) {
                    ticosClient.startService()
                }
                updateServiceStatus()
            } catch (e: Exception) {
                Log.e(TAG, "Error starting service", e)
            }
        }
    }
    
    private fun stopService() {
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    ticosClient.stopService()
                }
                updateServiceStatus()
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping service", e)
            }
        }
    }
    
    private fun restartService() {
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    ticosClient.restartService()
                }
                updateServiceStatus()
            } catch (e: Exception) {
                Log.e(TAG, "Error restarting service", e)
            }
        }
    }
    
    private fun updateServiceStatus() {
        lifecycleScope.launch {
            try {
                // 使用 TicosAgentClient 获取服务状态
                val status = withContext(Dispatchers.IO) {
                    if (ticosClient.isServiceBound()) {
                        ticosClient.getServiceStatus()
                    } else {
                        "disconnected"
                    }
                }
                
                val isRunning = status == "running"
                
                binding.statusText.text = if (isRunning) {
                    getString(R.string.service_running)
                } else {
                    getString(R.string.service_stopped)
                }
                
                // 更新按钮状态
                binding.startButton.isEnabled = !isRunning
                binding.stopButton.isEnabled = isRunning
                binding.restartButton.isEnabled = isRunning
            } catch (e: Exception) {
                Log.e(TAG, "Error updating service status", e)
            }
        }
    }
    
    private fun checkBatteryOptimization() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val powerManager = getSystemService(POWER_SERVICE) as PowerManager
            if (!powerManager.isIgnoringBatteryOptimizations(packageName)) {
                val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                }
                try {
                    startActivity(intent)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to request ignore battery optimizations", e)
                }
            }
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        when (requestCode) {
            1 -> {
                if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    Log.i(TAG, "RECORD_AUDIO permission granted")
                } else {
                    Log.e(TAG, "RECORD_AUDIO permission denied")
                }
            }
            2 -> {
                if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    Log.i(TAG, "CAMERA permission granted")
                } else {
                    Log.e(TAG, "CAMERA permission denied")
                }
            }
            3 -> {
                if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    Log.i(TAG, "WRITE_EXTERNAL_STORAGE permission granted")
                } else {
                    Log.e(TAG, "WRITE_EXTERNAL_STORAGE permission denied")
                }
            }
        }
        
        // 请求下一个权限
        requestNextPermission()
    }
}
