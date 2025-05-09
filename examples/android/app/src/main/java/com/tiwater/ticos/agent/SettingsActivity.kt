package com.tiwater.ticos.agent

import android.content.ComponentName
import android.content.Context
import android.content.ContentValues
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.IBinder
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.preference.EditTextPreference
import androidx.preference.ListPreference
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import androidx.preference.SeekBarPreference
import androidx.preference.SwitchPreferenceCompat
import com.akuleshov7.ktoml.Toml
import kotlinx.coroutines.delay
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import com.tiwater.ticos.common.TicosConfig
import com.tiwater.ticos.common.ConfigContract
import com.tiwater.ticos.common.ConfigConstants
import com.tiwater.ticos.common.WebSocketConfigImpl
import com.tiwater.ticos.service.TicosAgentClient
import com.tiwater.ticos.service.config.ConfigManager
import com.tiwater.ticos.service.device.DeviceManager
import android.app.AlertDialog
import android.net.Uri
import android.os.Environment
import android.view.LayoutInflater
import android.widget.EditText
import androidx.activity.result.contract.ActivityResultContracts
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

/**
 * Settings activity for configuring Ticos Agent
 */
class SettingsActivity : AppCompatActivity() {
    companion object {
        private const val TAG = "SettingsActivity"
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        
        if (savedInstanceState == null) {
            supportFragmentManager
                .beginTransaction()
                .replace(R.id.settings, SettingsFragment())
                .commit()
        }
        
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
    }
    
    /**
     * Settings fragment containing all preference items
     */
    class SettingsFragment : PreferenceFragmentCompat() {
        private var ticosClient: TicosAgentClient? = null
        private var isBound = false
        private lateinit var deviceManager: DeviceManager
        
        // 文件选择器结果处理
        private val importFileLauncher = registerForActivityResult(
            ActivityResultContracts.GetContent()
        ) { uri: Uri? ->
            uri?.let { importConfigFromUri(it) }
        }
        
        // 文件保存结果处理
        private val exportFileLauncher = registerForActivityResult(
            ActivityResultContracts.CreateDocument("text/toml")
        ) { uri: Uri? ->
            uri?.let { exportConfigToUri(it) }
        }
        
        override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
            setPreferencesFromResource(R.xml.root_preferences, rootKey)
            
            // Initialize managers
            deviceManager = DeviceManager(requireContext())
            ticosClient = TicosAgentClient(requireContext())
            
            // Bind service
            bindService()
            
            // Initialize device lists for selection
            initializeDeviceLists()

            // Set up import/export config click listeners
            findPreference<Preference>("import_config")?.setOnPreferenceClickListener {
                importFileLauncher.launch("*/*")
                true
            }
            
            findPreference<Preference>("export_config")?.setOnPreferenceClickListener {
                exportFileLauncher.launch("config.toml")
                true
            }
            
            // Set up edit config click listener
            findPreference<Preference>("edit_config")?.setOnPreferenceClickListener {
                showTomlConfigEditor()
                true
            }
            
            // Set up other preference change listeners
            setupPreferenceChangeListeners()
        }
        
        override fun onStart() {
            super.onStart()
            bindService()
        }
        
        override fun onStop() {
            super.onStop()
            ticosClient?.unbindService()
            isBound = false
        }
        
        private fun bindService() {
            ticosClient?.bindService { connected ->
                isBound = connected
                if (connected) {
                    loadCurrentConfig()
                }
            }
        }
        
        private fun loadCurrentConfig() {
            lifecycleScope.launch {
                try {
                    if (isBound && ticosClient != null) {
                        val configToml = withContext(Dispatchers.IO) {
                            ticosClient?.getServiceConfig()
                        }
                        
                        configToml?.let { toml ->
                            val config = TicosConfig.fromToml(toml)
                            updatePreferencesFromConfig(config)
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error loading config", e)
                    Toast.makeText(requireContext(), "Failed to load configuration", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        /**
         * 从界面控件更新配置值
         */
        private fun updatePreferencesFromConfig(config: TicosConfig) {
            // 更新基本配置
            findPreference<EditTextPreference>("api_key")?.text = config.api.apiKey
            findPreference<EditTextPreference>("agent_id")?.text = config.agentId
            findPreference<EditTextPreference>("protocol")?.text = config.api.protocol
            findPreference<EditTextPreference>("host")?.text = config.api.host
            
            // 更新麦克风配置
            findPreference<EditTextPreference>("microphone_component")?.text = config.microphone.component
            // findPreference<ListPreference>("audio_input_device")?.value = config.microphone.device
            // findPreference<SeekBarPreference>("microphone_volume")?.value = (config.microphone.volume * 100).toInt()
            
            // 更新扬声器配置
            findPreference<EditTextPreference>("speaker_component")?.text = config.speaker.component
            // findPreference<ListPreference>("audio_output_device")?.value = config.speaker.device
            // findPreference<SeekBarPreference>("speaker_volume")?.value = (config.speaker.volume * 100).toInt()
            findPreference<EditTextPreference>("speaker_buffer_time")?.text = config.speaker.bufferTime.toString()
            findPreference<EditTextPreference>("speaker_latency_time")?.text = config.speaker.latencyTime.toString()
            findPreference<SwitchPreferenceCompat>("speaker_sync")?.isChecked = config.speaker.sync
            
            // 更新摄像头配置
            findPreference<SwitchPreferenceCompat>("enable_camera")?.isChecked = config.camera.enable
            
            // 添加日志记录 camera_component 的值
            findPreference<EditTextPreference>("camera_component")?.text = config.camera.component
            
            findPreference<ListPreference>("camera_device")?.value = config.camera.device
            findPreference<SwitchPreferenceCompat>("camera_visualvoice_enabled")?.isChecked = config.camera.visualvoiceEnabled
            findPreference<SwitchPreferenceCompat>("camera_upload_enabled")?.isChecked = config.camera.uploadEnabled
            
            // 更新实时配置
            findPreference<EditTextPreference>("buffer_time_ms")?.text = config.realtime.bufferTimeMs.toString()
            findPreference<ListPreference>("voice")?.value = config.realtime.voice
            findPreference<SwitchPreferenceCompat>("turn_detection")?.isChecked = config.realtime.turnDetection
            
            // 更新实时 WebSocket 配置
            findPreference<EditTextPreference>("max_reconnect_attempts")?.text = config.realtime.websocket.maxReconnectAttempts.toString()
            findPreference<EditTextPreference>("reconnect_delay_ms")?.text = config.realtime.websocket.reconnectDelayMs.toString()
            findPreference<EditTextPreference>("connection_timeout_ms")?.text = config.realtime.websocket.connectionTimeoutMs.toString()
            
            // 更新实时模型配置
            findPreference<EditTextPreference>("model")?.text = config.realtime.model.name
            findPreference<EditTextPreference>("model_provider")?.text = config.realtime.model.provider
            findPreference<EditTextPreference>("instructions")?.text = config.realtime.model.instructions
            
            // 更新实时视觉配置
            findPreference<SwitchPreferenceCompat>("enable_face_detection")?.isChecked = config.realtime.vision.enableFaceDetection
            findPreference<SwitchPreferenceCompat>("enable_face_identification")?.isChecked = config.realtime.vision.enableFaceIdentification
            findPreference<SwitchPreferenceCompat>("enable_object_detection")?.isChecked = config.realtime.vision.enableObjectDetection
            
            // 更新 VAD 配置
            findPreference<SeekBarPreference>("vad_threshold")?.value = (config.vad.voiceActivityThreshold * 100).toInt()
            findPreference<EditTextPreference>("min_audio_duration_ms")?.text = config.vad.minAudioDurationMs.toString()
            findPreference<EditTextPreference>("silence_duration_ms")?.text = config.vad.silenceDurationMs.toString()
            findPreference<EditTextPreference>("silence_threshold")?.text = config.vad.silenceThreshold.toString()
            findPreference<EditTextPreference>("debounce_time_ms")?.text = config.vad.debounceTimeMs.toString()
            findPreference<EditTextPreference>("hold_time_ms")?.text = config.vad.holdTimeMs.toString()
            findPreference<EditTextPreference>("audio_sync_delay_ms")?.text = config.vad.audioSyncDelayMs.toString()
            
            // 更新执行器配置
            findPreference<EditTextPreference>("executor_addr")?.text = config.executor.addr
            
            // 更新视频上传配置
            findPreference<EditTextPreference>("video_upload_fps")?.text = config.videoUpload.fps.toString()
            
            // 更新视频上传 WebSocket 配置
            findPreference<EditTextPreference>("video_upload_max_reconnect_attempts")?.text = config.videoUpload.maxReconnectAttempts.toString()
            findPreference<EditTextPreference>("video_upload_reconnect_delay_ms")?.text = config.videoUpload.reconnectDelayMs.toString()
            findPreference<EditTextPreference>("video_upload_connection_timeout_ms")?.text = config.videoUpload.connectionTimeoutMs.toString()
        }
        
        /**
         * 从界面控件保存配置值到 TicosConfig 对象
         */
        private fun savePreferencesToConfig(): TicosConfig {
            val currentConfig = ticosClient?.getServiceConfig()?.let { TicosConfig.fromToml(it) } ?: TicosConfig()
            
            // 创建一个新的配置对象，基于当前配置但更新了界面上的值
            return currentConfig.copy(
                agentId = findPreference<EditTextPreference>("agent_id")?.text ?: currentConfig.agentId,
                
                // 更新 API 配置
                api = currentConfig.api.copy(
                    apiKey = findPreference<EditTextPreference>("api_key")?.text ?: currentConfig.api.apiKey,
                    protocol = findPreference<EditTextPreference>("protocol")?.text ?: currentConfig.api.protocol,
                    host = findPreference<EditTextPreference>("host")?.text ?: currentConfig.api.host
                ),
                
                // 更新麦克风配置
                microphone = currentConfig.microphone.copy(
                    component = findPreference<EditTextPreference>("microphone_component")?.text ?: currentConfig.microphone.component,
                    // device = findPreference<ListPreference>("audio_input_device")?.value ?: currentConfig.microphone.device,
                    // volume = findPreference<SeekBarPreference>("microphone_volume")?.value?.toDouble()?.div(100) ?: currentConfig.microphone.volume
                ),
                
                // 更新扬声器配置
                speaker = currentConfig.speaker.copy(
                    component = findPreference<EditTextPreference>("speaker_component")?.text ?: currentConfig.speaker.component,
                    // device = findPreference<ListPreference>("audio_output_device")?.value ?: currentConfig.speaker.device,
                    // volume = findPreference<SeekBarPreference>("speaker_volume")?.value?.toDouble()?.div(100) ?: currentConfig.speaker.volume,
                    bufferTime = findPreference<EditTextPreference>("speaker_buffer_time")?.text?.toIntOrNull() ?: currentConfig.speaker.bufferTime,
                    latencyTime = findPreference<EditTextPreference>("speaker_latency_time")?.text?.toIntOrNull() ?: currentConfig.speaker.latencyTime,
                    sync = findPreference<SwitchPreferenceCompat>("speaker_sync")?.isChecked ?: currentConfig.speaker.sync
                ),
                
                // 更新摄像头配置
                camera = currentConfig.camera.copy(
                    enable = findPreference<SwitchPreferenceCompat>("enable_camera")?.isChecked ?: currentConfig.camera.enable,
                    component = findPreference<EditTextPreference>("camera_component")?.text ?: currentConfig.camera.component,
                    device = findPreference<ListPreference>("camera_device")?.value ?: currentConfig.camera.device,
                    visualvoiceEnabled = findPreference<SwitchPreferenceCompat>("camera_visualvoice_enabled")?.isChecked ?: currentConfig.camera.visualvoiceEnabled,
                    uploadEnabled = findPreference<SwitchPreferenceCompat>("camera_upload_enabled")?.isChecked ?: currentConfig.camera.uploadEnabled
                ),
                
                // 更新实时配置
                realtime = currentConfig.realtime.copy(
                    bufferTimeMs = findPreference<EditTextPreference>("buffer_time_ms")?.text?.toIntOrNull() ?: currentConfig.realtime.bufferTimeMs,
                    voice = findPreference<ListPreference>("voice")?.value ?: currentConfig.realtime.voice,
                    turnDetection = findPreference<SwitchPreferenceCompat>("turn_detection")?.isChecked ?: currentConfig.realtime.turnDetection,
                    
                    // 更新 WebSocket 配置
                    websocket = com.tiwater.ticos.common.WebSocketConfigImpl(
                        maxReconnectAttempts = findPreference<EditTextPreference>("max_reconnect_attempts")?.text?.toIntOrNull() 
                            ?: (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.maxReconnectAttempts 
                            ?: ConfigConstants.DEFAULT_MAX_RECONNECT_ATTEMPTS,
                        reconnectDelayMs = findPreference<EditTextPreference>("reconnect_delay_ms")?.text?.toIntOrNull() 
                            ?: (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.reconnectDelayMs 
                            ?: ConfigConstants.DEFAULT_RECONNECT_DELAY_MS,
                        connectionTimeoutMs = findPreference<EditTextPreference>("connection_timeout_ms")?.text?.toIntOrNull() 
                            ?: (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.connectionTimeoutMs 
                            ?: ConfigConstants.DEFAULT_CONNECTION_TIMEOUT_MS
                    ),
                    
                    // 更新模型配置
                    model = currentConfig.realtime.model.copy(
                        name = findPreference<EditTextPreference>("model")?.text ?: currentConfig.realtime.model.name,
                        provider = findPreference<EditTextPreference>("model_provider")?.text ?: currentConfig.realtime.model.provider,
                        instructions = findPreference<EditTextPreference>("instructions")?.text ?: currentConfig.realtime.model.instructions
                    ),
                    
                    // 更新视觉配置
                    vision = currentConfig.realtime.vision.copy(
                        enableFaceDetection = findPreference<SwitchPreferenceCompat>("enable_face_detection")?.isChecked ?: currentConfig.realtime.vision.enableFaceDetection,
                        enableFaceIdentification = findPreference<SwitchPreferenceCompat>("enable_face_identification")?.isChecked ?: currentConfig.realtime.vision.enableFaceIdentification,
                        enableObjectDetection = findPreference<SwitchPreferenceCompat>("enable_object_detection")?.isChecked ?: currentConfig.realtime.vision.enableObjectDetection
                    )
                ),
                
                // 更新 VAD 配置
                vad = currentConfig.vad.copy(
                    voiceActivityThreshold = findPreference<SeekBarPreference>("vad_threshold")?.value?.toFloat()?.div(100) ?: currentConfig.vad.voiceActivityThreshold,
                    minAudioDurationMs = findPreference<EditTextPreference>("min_audio_duration_ms")?.text?.toIntOrNull() ?: currentConfig.vad.minAudioDurationMs,
                    silenceDurationMs = findPreference<EditTextPreference>("silence_duration_ms")?.text?.toIntOrNull() ?: currentConfig.vad.silenceDurationMs,
                    silenceThreshold = findPreference<EditTextPreference>("silence_threshold")?.text?.toIntOrNull() ?: currentConfig.vad.silenceThreshold,
                    debounceTimeMs = findPreference<EditTextPreference>("debounce_time_ms")?.text?.toIntOrNull() ?: currentConfig.vad.debounceTimeMs,
                    holdTimeMs = findPreference<EditTextPreference>("hold_time_ms")?.text?.toIntOrNull() ?: currentConfig.vad.holdTimeMs,
                    audioSyncDelayMs = findPreference<EditTextPreference>("audio_sync_delay_ms")?.text?.toIntOrNull() ?: currentConfig.vad.audioSyncDelayMs
                ),
                
                // 更新执行器配置
                executor = currentConfig.executor.copy(
                    addr = findPreference<EditTextPreference>("executor_addr")?.text ?: currentConfig.executor.addr
                ),
                
                // 更新视频上传配置
                videoUpload = currentConfig.videoUpload.copy(
                    fps = findPreference<EditTextPreference>("video_upload_fps")?.text?.toIntOrNull() ?: currentConfig.videoUpload.fps,
                    maxReconnectAttempts = findPreference<EditTextPreference>("video_upload_max_reconnect_attempts")?.text?.toIntOrNull() ?: currentConfig.videoUpload.maxReconnectAttempts,
                    reconnectDelayMs = findPreference<EditTextPreference>("video_upload_reconnect_delay_ms")?.text?.toIntOrNull() ?: currentConfig.videoUpload.reconnectDelayMs,
                    connectionTimeoutMs = findPreference<EditTextPreference>("video_upload_connection_timeout_ms")?.text?.toIntOrNull() ?: currentConfig.videoUpload.connectionTimeoutMs
                )
            )
        }
        
        /**
         * Initialize device lists (audio input/output, camera) for selection
         * 设备选择初始化，确保界面可以选择各类设备
         */
        private fun initializeDeviceLists() {
            // --- Audio Input Devices ---
            // val audioInputPref = findPreference<ListPreference>("audio_input_device")
            // val audioInputDevices = deviceManager.getAudioInputDevices()
            
            // if (audioInputPref != null) {
            //     if (audioInputDevices.isNotEmpty()) {
            //         val entries = audioInputDevices.map { it.name }.toTypedArray()
            //         val entryValues = audioInputDevices.map { it.id }.toTypedArray()
            //         audioInputPref.entries = entries
            //         audioInputPref.entryValues = entryValues
            //     }
            // }
            
            // // --- Audio Output Devices ---
            // val audioOutputPref = findPreference<ListPreference>("audio_output_device")
            // val audioOutputDevices = deviceManager.getAudioOutputDevices()
            
            // if (audioOutputPref != null) {
            //     if (audioOutputDevices.isNotEmpty()) {
            //         val entries = audioOutputDevices.map { it.name }.toTypedArray()
            //         val entryValues = audioOutputDevices.map { it.id }.toTypedArray()
            //         audioOutputPref.entries = entries
            //         audioOutputPref.entryValues = entryValues
            //     }
            // }
            
            // --- Camera Devices ---
            val cameraPref = findPreference<ListPreference>("camera_device")
            val cameraDevices = deviceManager.getCameraDevices()
            
            if (cameraPref != null) {
                if (cameraDevices.isNotEmpty()) {
                    val entries = cameraDevices.map { it.name }.toTypedArray()
                    val entryValues = cameraDevices.map { it.id }.toTypedArray()
                    cameraPref.entries = entries
                    cameraPref.entryValues = entryValues
                }
            }
        }
        
        private fun setupPreferenceChangeListeners() {
            // API 设置
            findPreference<EditTextPreference>("api_key")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("api_key", newValue as String)
                true
            }
            
            findPreference<EditTextPreference>("host")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("host", newValue as String)
                true
            }
            
            findPreference<EditTextPreference>("protocol")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("protocol", newValue as String)
                true
            }
            
            // agent_id 设置
            findPreference<EditTextPreference>("agent_id")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("agent_id", newValue as String)
                true
            }
            
            // 模型设置
            findPreference<EditTextPreference>("model")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("model", newValue as String)
                true
            }
            
            // 添加 model_provider 的监听器
            findPreference<EditTextPreference>("model_provider")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("model_provider", newValue as String)
                true
            }
            
            findPreference<EditTextPreference>("instructions")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("instructions", newValue as String)
                true
            }
            
            findPreference<ListPreference>("voice")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("voice", newValue as String)
                true
            }
            
            // 添加 turn_detection 的监听器
            findPreference<SwitchPreferenceCompat>("turn_detection")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("turn_detection", newValue as Boolean)
                true
            }
            
            // 麦克风设置
            // findPreference<SeekBarPreference>("microphone_volume")?.setOnPreferenceChangeListener { _, newValue ->
            //     val volume = (newValue as Int).toFloat() / 100.0f
            //     updateConfigValue("microphone_volume", volume)
            //     true
            // }
            
            findPreference<SwitchPreferenceCompat>("denoise")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("denoise", newValue as Boolean)
                true
            }
            
            // findPreference<ListPreference>("audio_input_device")?.setOnPreferenceChangeListener { _, newValue ->
            //     updateConfigValue("audio_input_device", newValue as String)
            //     true
            // }
            
            // 添加 microphone_component 的监听器
            findPreference<EditTextPreference>("microphone_component")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("microphone_component", newValue as String)
                true
            }
            
            // 扬声器设置
            // findPreference<SeekBarPreference>("speaker_volume")?.setOnPreferenceChangeListener { _, newValue ->
            //     val volume = (newValue as Int).toFloat() / 100.0f
            //     updateConfigValue("speaker_volume", volume)
            //     true
            // }
            
            // findPreference<ListPreference>("audio_output_device")?.setOnPreferenceChangeListener { _, newValue ->
            //     updateConfigValue("audio_output_device", newValue as String)
            //     true
            // }
            
            // 添加 speaker_component 的监听器
            findPreference<EditTextPreference>("speaker_component")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("speaker_component", newValue as String)
                true
            }
            
            // 添加 speaker_buffer_time 的监听器
            findPreference<EditTextPreference>("speaker_buffer_time")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val bufferTime = (newValue as String).toInt()
                    updateConfigValue("speaker_buffer_time", bufferTime)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 speaker_latency_time 的监听器
            findPreference<EditTextPreference>("speaker_latency_time")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val latencyTime = (newValue as String).toInt()
                    updateConfigValue("speaker_latency_time", latencyTime)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 speaker_sync 的监听器
            findPreference<SwitchPreferenceCompat>("speaker_sync")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("speaker_sync", newValue as Boolean)
                true
            }
            
            // 摄像头设置
            findPreference<SwitchPreferenceCompat>("enable_camera")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("enable_camera", newValue as Boolean)
                true
            }
            
            // 添加 camera_component 的监听器
            findPreference<EditTextPreference>("camera_component")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("camera_component", newValue as String)
                true
            }
            
            findPreference<ListPreference>("camera_device")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("camera_device", newValue as String)
                true
            }
            
            // 添加 camera_upload_enabled 的监听器
            findPreference<SwitchPreferenceCompat>("camera_upload_enabled")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("camera_upload_enabled", newValue as Boolean)
                true
            }
            
            // 添加 camera_visualvoice_enabled 的监听器
            findPreference<SwitchPreferenceCompat>("camera_visualvoice_enabled")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("camera_visualvoice_enabled", newValue as Boolean)
                true
            }
            
            // 添加 video_upload_fps 的监听器
            findPreference<EditTextPreference>("video_upload_fps")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val fps = (newValue as String).toInt()
                    updateConfigValue("video_upload_fps", fps)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 buffer_time_ms 的监听器
            findPreference<EditTextPreference>("buffer_time_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val bufferTime = (newValue as String).toInt()
                    updateConfigValue("buffer_time_ms", bufferTime)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // VAD 设置
            findPreference<SeekBarPreference>("vad_threshold")?.setOnPreferenceChangeListener { _, newValue ->
                val threshold = (newValue as Int).toFloat() / 100.0f
                updateConfigValue("vad_threshold", threshold)
                true
            }
            
            findPreference<EditTextPreference>("silence_duration_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val duration = (newValue as String).toInt()
                    updateConfigValue("silence_duration_ms", duration)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 min_audio_duration_ms 的监听器
            findPreference<EditTextPreference>("min_audio_duration_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val value = (newValue as String).toInt()
                    updateConfigValue("min_audio_duration_ms", value)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 audio_sync_delay_ms 的监听器
            findPreference<EditTextPreference>("audio_sync_delay_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val delay = (newValue as String).toInt()
                    updateConfigValue("audio_sync_delay_ms", delay)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 debounce_time_ms 的监听器
            findPreference<EditTextPreference>("debounce_time_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val time = (newValue as String).toInt()
                    updateConfigValue("debounce_time_ms", time)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 hold_time_ms 的监听器
            findPreference<EditTextPreference>("hold_time_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val time = (newValue as String).toInt()
                    updateConfigValue("hold_time_ms", time)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 connection_timeout_ms 的监听器
            findPreference<EditTextPreference>("connection_timeout_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val timeout = (newValue as String).toInt()
                    updateConfigValue("connection_timeout_ms", timeout)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 reconnect_delay_ms 的监听器
            findPreference<EditTextPreference>("reconnect_delay_ms")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val delay = (newValue as String).toInt()
                    updateConfigValue("reconnect_delay_ms", delay)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 max_reconnect_attempts 的监听器
            findPreference<EditTextPreference>("max_reconnect_attempts")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val attempts = (newValue as String).toInt()
                    updateConfigValue("max_reconnect_attempts", attempts)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
            
            // 添加 executor_addr 的监听器
            findPreference<EditTextPreference>("executor_addr")?.setOnPreferenceChangeListener { _, newValue ->
                updateConfigValue("executor_addr", newValue as String)
                true
            }
            
            // 添加 silence_threshold 的监听器
            findPreference<EditTextPreference>("silence_threshold")?.setOnPreferenceChangeListener { _, newValue ->
                try {
                    val value = (newValue as String).toInt()
                    updateConfigValue("silence_threshold", value)
                    true
                } catch (e: NumberFormatException) {
                    Toast.makeText(requireContext(), "请输入有效的数字", Toast.LENGTH_SHORT).show()
                    false
                }
            }
        }
        
        private fun updateConfigValue(key: String, value: Any) {
            
            lifecycleScope.launch {
                try {
                    // 获取当前完整配置
                    val currentConfig = ticosClient?.getServiceConfig()?.let { TicosConfig.fromToml(it) } ?: TicosConfig()
                    
                    // 根据 key 更新特定配置项
                    val updatedConfig = when (key) {
                        // API 配置
                        "api_key" -> currentConfig.copy(
                            api = currentConfig.api.copy(apiKey = value as String)
                        )
                        "host" -> currentConfig.copy(
                            api = currentConfig.api.copy(host = value as String)
                        )
                        "protocol" -> currentConfig.copy(
                            api = currentConfig.api.copy(protocol = value as String)
                        )
                        
                        // 基本配置
                        "agent_id" -> currentConfig.copy(
                            agentId = value as String
                        )
                        
                        // 麦克风配置
                        "microphone_component" -> currentConfig.copy(
                            microphone = currentConfig.microphone.copy(component = value as String)
                        )
                        // "audio_input_device" -> currentConfig.copy(
                        //     microphone = currentConfig.microphone.copy(device = value as String)
                        // )
                        // "microphone_volume" -> currentConfig.copy(
                        //     microphone = currentConfig.microphone.copy(volume = (value as Float).toDouble())
                        // )
                        "denoise" -> currentConfig.copy(
                            microphone = currentConfig.microphone.copy() // 降噪设置，如果需要添加到 TicosConfig 中
                        )
                        
                        // 扬声器配置
                        "speaker_component" -> currentConfig.copy(
                            speaker = currentConfig.speaker.copy(component = value as String)
                        )
                        // "audio_output_device" -> currentConfig.copy(
                        //     speaker = currentConfig.speaker.copy(device = value as String)
                        // )
                        // "speaker_volume" -> currentConfig.copy(
                        //     speaker = currentConfig.speaker.copy(volume = (value as Float).toDouble())
                        // )
                        "speaker_buffer_time" -> currentConfig.copy(
                            speaker = currentConfig.speaker.copy(bufferTime = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "speaker_latency_time" -> currentConfig.copy(
                            speaker = currentConfig.speaker.copy(latencyTime = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "speaker_sync" -> currentConfig.copy(
                            speaker = currentConfig.speaker.copy(sync = value as Boolean)
                        )
                        
                        // 摄像头配置
                        "enable_camera" -> currentConfig.copy(
                            camera = currentConfig.camera.copy(enable = value as Boolean)
                        )
                        "camera_component" -> {
                            val updatedConfig = currentConfig.copy(
                                camera = currentConfig.camera.copy(component = value as String)
                            )
                            updatedConfig
                        }
                        "camera_device" -> currentConfig.copy(
                            camera = currentConfig.camera.copy(device = value as String)
                        )
                        "camera_visualvoice_enabled" -> currentConfig.copy(
                            camera = currentConfig.camera.copy(visualvoiceEnabled = value as Boolean)
                        )
                        "camera_upload_enabled" -> currentConfig.copy(
                            camera = currentConfig.camera.copy(uploadEnabled = value as Boolean)
                        )
                        
                        // 实时配置
                        "buffer_time_ms" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(bufferTimeMs = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "voice" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(voice = value as String)
                        )
                        "turn_detection" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(turnDetection = value as Boolean)
                        )
                        "model" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                model = currentConfig.realtime.model.copy(name = value as String)
                            )
                        )
                        "model_provider" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                model = currentConfig.realtime.model.copy(provider = value as String)
                            )
                        )
                        "instructions" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                model = currentConfig.realtime.model.copy(instructions = value as String)
                            )
                        )
                        
                        // WebSocket 配置
                        "max_reconnect_attempts" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                websocket = com.tiwater.ticos.common.WebSocketConfigImpl(
                                    maxReconnectAttempts = when(value) {
                                        is String -> value.toInt()
                                        is Int -> value
                                        else -> throw ClassCastException("Cannot convert $value to Int")
                                    },
                                    reconnectDelayMs = (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.reconnectDelayMs 
                                        ?: ConfigConstants.DEFAULT_RECONNECT_DELAY_MS,
                                    connectionTimeoutMs = (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.connectionTimeoutMs 
                                        ?: ConfigConstants.DEFAULT_CONNECTION_TIMEOUT_MS
                                )
                            )
                        )
                        "reconnect_delay_ms" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                websocket = com.tiwater.ticos.common.WebSocketConfigImpl(
                                    maxReconnectAttempts = (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.maxReconnectAttempts 
                                        ?: ConfigConstants.DEFAULT_MAX_RECONNECT_ATTEMPTS,
                                    reconnectDelayMs = when(value) {
                                        is String -> value.toInt()
                                        is Int -> value
                                        else -> throw ClassCastException("Cannot convert $value to Int")
                                    },
                                    connectionTimeoutMs = (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.connectionTimeoutMs 
                                        ?: ConfigConstants.DEFAULT_CONNECTION_TIMEOUT_MS
                                )
                            )
                        )
                        "connection_timeout_ms" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                websocket = com.tiwater.ticos.common.WebSocketConfigImpl(
                                    maxReconnectAttempts = (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.maxReconnectAttempts 
                                        ?: ConfigConstants.DEFAULT_MAX_RECONNECT_ATTEMPTS,
                                    reconnectDelayMs = (currentConfig.realtime.websocket as? com.tiwater.ticos.common.WebSocketConfigImpl)?.reconnectDelayMs 
                                        ?: ConfigConstants.DEFAULT_RECONNECT_DELAY_MS,
                                    connectionTimeoutMs = when(value) {
                                        is String -> value.toInt()
                                        is Int -> value
                                        else -> throw ClassCastException("Cannot convert $value to Int")
                                    }
                                )
                            )
                        )
                        
                        // 视觉配置
                        "enable_face_detection" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                vision = currentConfig.realtime.vision.copy(
                                    enableFaceDetection = value as Boolean
                                )
                            )
                        )
                        "enable_face_identification" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                vision = currentConfig.realtime.vision.copy(
                                    enableFaceIdentification = value as Boolean
                                )
                            )
                        )
                        "enable_object_detection" -> currentConfig.copy(
                            realtime = currentConfig.realtime.copy(
                                vision = currentConfig.realtime.vision.copy(
                                    enableObjectDetection = value as Boolean
                                )
                            )
                        )
                        
                        // VAD 配置
                        "vad_threshold" -> currentConfig.copy(
                            vad = currentConfig.vad.copy(voiceActivityThreshold = value as Float)
                        )
                        "min_audio_duration_ms" -> currentConfig.copy(
                            vad = currentConfig.vad.copy(minAudioDurationMs = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "silence_duration_ms" -> currentConfig.copy(
                            vad = currentConfig.vad.copy(silenceDurationMs = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "silence_threshold" -> currentConfig.copy(
                            vad = currentConfig.vad.copy(silenceThreshold = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "debounce_time_ms" -> currentConfig.copy(
                            vad = currentConfig.vad.copy(debounceTimeMs = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "hold_time_ms" -> currentConfig.copy(
                            vad = currentConfig.vad.copy(holdTimeMs = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        "audio_sync_delay_ms" -> currentConfig.copy(
                            vad = currentConfig.vad.copy(audioSyncDelayMs = when(value) {
                                is String -> value.toInt()
                                is Int -> value
                                else -> throw ClassCastException("Cannot convert $value to Int")
                            })
                        )
                        
                        // 执行器配置
                        "executor_addr" -> currentConfig.copy(
                            executor = currentConfig.executor.copy(addr = value as String)
                        )
                        
                        // 视频上传配置
                        "video_upload_fps" -> currentConfig.copy(
                            videoUpload = currentConfig.videoUpload.copy(
                                fps = when(value) {
                                    is String -> value.toInt()
                                    is Int -> value
                                    else -> throw ClassCastException("Cannot convert $value to Int")
                                }
                            )
                        )
                        "video_upload_max_reconnect_attempts" -> currentConfig.copy(
                            videoUpload = currentConfig.videoUpload.copy(
                                maxReconnectAttempts = when (value) {
                                    is String -> value.toInt()
                                    is Int -> value
                                    else -> throw ClassCastException("Cannot convert $value to Int")
                                }
                            )
                        )
                        "video_upload_reconnect_delay_ms" -> currentConfig.copy(
                            videoUpload = currentConfig.videoUpload.copy(
                                reconnectDelayMs = when(value) {
                                    is String -> value.toInt()
                                    is Int -> value
                                    else -> throw ClassCastException("Cannot convert $value to Int")
                                }
                            )
                        )
                        "video_upload_connection_timeout_ms" -> currentConfig.copy(
                            videoUpload = currentConfig.videoUpload.copy(
                                connectionTimeoutMs = when(value) {
                                    is String -> value.toInt()
                                    is Int -> value
                                    else -> throw ClassCastException("Cannot convert $value to Int")
                                }
                            )
                        )
                        
                        // 默认情况
                        else -> {
                            Log.w(TAG, "未处理的配置项: $key = $value")
                            currentConfig
                        }
                    }
                    
                    // 通过 TicosAgentClient 更新配置
                    withContext(Dispatchers.IO) {
                        ticosClient?.updateServiceConfig(updatedConfig.toToml())
                    }
                    
                    Log.d(TAG, "Config updated: $key = $value")
                } catch (e: Exception) {
                    Log.e(TAG, "Error updating config value", e)
                    Toast.makeText(requireContext(), "Failed to update config: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        /**
         * 从 URI 导入配置
         */
        private fun importConfigFromUri(uri: Uri) {
            lifecycleScope.launch {
                try {
                    // 检查服务是否已绑定
                    if (!isBound || ticosClient == null) {
                        bindService()
                        delay(300) // 适当延迟等待服务连接
                    }
                    val inputStream = requireContext().contentResolver.openInputStream(uri)
                    val configToml = inputStream?.bufferedReader().use { it?.readText() } ?: ""
                    
                    // 验证 TOML 格式是否有效
                    try {
                        TicosConfig.fromToml(configToml)
                    } catch (e: Exception) {
                        Toast.makeText(requireContext(), "Invalid TOML format: ${e.message}", Toast.LENGTH_SHORT).show()
                        return@launch
                    }
                    
                    // 保存配置
                    withContext(Dispatchers.IO) {
                        ticosClient?.updateServiceConfig(configToml)
                    }
                    
                    // 重新加载配置到 UI
                    loadCurrentConfig()
                    
                    Toast.makeText(requireContext(), "Configuration imported successfully", Toast.LENGTH_SHORT).show()
                } catch (e: Exception) {
                    Log.e(TAG, "Error importing config", e)
                    Toast.makeText(requireContext(), "Failed to import configuration: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        /**
         * 导出配置到 URI
         */
        private fun exportConfigToUri(uri: Uri) {
            lifecycleScope.launch {
                try {
                    // 检查服务是否已绑定
                    if (!isBound || ticosClient == null) {
                        bindService()
                        delay(300) // 适当延迟等待服务连接
                    }
                    
                    val configToml = withContext(Dispatchers.IO) {
                        ticosClient?.getServiceConfig().also { 
                            Log.d(TAG, "Exported config length: ${it?.length ?: 0}")
                            Log.d(TAG, "Exported config content: $it")
                        }
                    }
                    
                    if (configToml != null && configToml.isNotEmpty()) {
                        Log.d(TAG, "Writing config to URI: $uri")
                        val outputStream = requireContext().contentResolver.openOutputStream(uri)
                        outputStream?.use {
                            it.write(configToml.toByteArray())
                        }
                        
                        Toast.makeText(requireContext(), "Configuration exported successfully", Toast.LENGTH_SHORT).show()
                    } else {
                        Log.e(TAG, "Failed to export config: configToml is null or empty")
                        Toast.makeText(requireContext(), "Failed to export configuration: service not ready", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error exporting config", e)
                    Toast.makeText(requireContext(), "Failed to export configuration: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        // 显示 TOML 配置编辑器对话框
        private fun showTomlConfigEditor() {
            if (!isBound || ticosClient == null) {
                Toast.makeText(requireContext(), "Service not connected", Toast.LENGTH_SHORT).show()
                return
            }
            
            // 创建对话框视图
            val dialogView = LayoutInflater.from(requireContext()).inflate(R.layout.dialog_edit_toml, null)
            val editText = dialogView.findViewById<EditText>(R.id.edit_toml)
            
            // 获取当前配置
            lifecycleScope.launch {
                try {
                    val currentConfig = withContext(Dispatchers.IO) {
                        ticosClient?.getServiceConfig()
                    }
                    
                    if (currentConfig != null) {
                        editText.setText(currentConfig)
                        
                        // 创建并显示对话框
                        AlertDialog.Builder(requireContext())
                            .setTitle(R.string.dialog_edit_toml_title)
                            .setView(dialogView)
                            .setPositiveButton(R.string.dialog_save) { _, _ ->
                                // 保存修改后的配置
                                val editedToml = editText.text.toString()
                                saveTomlConfig(editedToml)
                            }
                            .setNegativeButton(R.string.dialog_cancel, null)
                            .show()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error loading config for TOML editor", e)
                    Toast.makeText(requireContext(), "Failed to load configuration: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        // 保存 TOML 格式的配置
        private fun saveTomlConfig(tomlConfig: String) {
            lifecycleScope.launch {
                try {
                    // 验证 TOML 格式是否有效
                    try {
                        TicosConfig.fromToml(tomlConfig)
                    } catch (e: Exception) {
                        Toast.makeText(requireContext(), "Invalid TOML format: ${e.message}", Toast.LENGTH_SHORT).show()
                        return@launch
                    }
                    
                    // 保存配置
                    withContext(Dispatchers.IO) {
                        ticosClient?.updateServiceConfig(tomlConfig)
                    }
                    
                    // 重新加载配置到 UI
                    loadCurrentConfig()
                    
                    Toast.makeText(requireContext(), R.string.toast_config_saved, Toast.LENGTH_SHORT).show()
                } catch (e: Exception) {
                    Log.e(TAG, "Error saving TOML config", e)
                    Toast.makeText(requireContext(), "Failed to save configuration: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        companion object {
            private const val TAG = "SettingsFragment"
        }
    }
}
