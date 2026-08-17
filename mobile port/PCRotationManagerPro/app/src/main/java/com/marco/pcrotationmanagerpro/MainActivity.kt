package com.marco.pcrotationmanagerpro

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.marco.pcrotationmanagerpro.api.ApiService
import com.marco.pcrotationmanagerpro.api.StatusResponse
import com.marco.pcrotationmanagerpro.service.PollingService
import com.marco.pcrotationmanagerpro.ui.screens.MainScreen
import com.marco.pcrotationmanagerpro.ui.theme.DarkBackground
import com.marco.pcrotationmanagerpro.ui.theme.PCRotationManagerProTheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.coroutines.coroutineContext

class MainActivity : ComponentActivity() {

    private lateinit var apiService: ApiService

    // Permission launcher for notifications (Android 13+)
    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            PollingService.start(this)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Set status bar color to match dark theme
        window.statusBarColor = 0xFF121212.toInt()
        window.decorView.systemUiVisibility = 0

        apiService = ApiService()

        // Request notification permission, then start foreground service
        requestNotificationPermission()

        setContent {
            PCRotationManagerProTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = DarkBackground
                ) {
                    var status by remember { mutableStateOf<StatusResponse?>(null) }
                    var isConnected by remember { mutableStateOf(false) }
                    var connectionText by remember { mutableStateOf("Connecting...") }
                    var showBreakDialog by remember { mutableStateOf(false) }
                    var showStopBreakDialog by remember { mutableStateOf(false) }

                    MainScreen(
                        status = status,
                        connectionStatus = connectionText,
                        isConnected = isConnected,
                        showBreakDialog = showBreakDialog,
                        showStopBreakDialog = showStopBreakDialog,
                        onShowBreakDialog = { showBreakDialog = true },
                        onDismissBreakDialog = { showBreakDialog = false },
                        onStartBreak = { reason, secretCode ->
                            lifecycleScope.launch {
                                val result = apiService.startPlayerBreak(reason, secretCode)
                                result.onSuccess {
                                    showBreakDialog = false
                                    connectionText = "Break started"
                                    Toast.makeText(
                                        this@MainActivity,
                                        "Break started",
                                        Toast.LENGTH_SHORT
                                    ).show()
                                }
                                result.onFailure { e ->
                                    connectionText = "Break failed"
                                    Toast.makeText(
                                        this@MainActivity,
                                        "Wrong code or error: ${e.message}",
                                        Toast.LENGTH_LONG
                                    ).show()
                                }
                                fetchAndUpdate { s ->
                                    status = s
                                    isConnected = true
                                    connectionText = "Online"
                                }
                            }
                        },
                        onShowStopBreakDialog = { showStopBreakDialog = true },
                        onDismissStopBreakDialog = { showStopBreakDialog = false },
                        onStopBreak = { secretCode ->
                            lifecycleScope.launch {
                                val result = apiService.stopPlayerBreak(secretCode)
                                result.onSuccess {
                                    showStopBreakDialog = false
                                    connectionText = "Break ended"
                                    Toast.makeText(
                                        this@MainActivity,
                                        "Break ended",
                                        Toast.LENGTH_SHORT
                                    ).show()
                                }
                                result.onFailure { e ->
                                    connectionText = "Stop failed"
                                    Toast.makeText(
                                        this@MainActivity,
                                        "Wrong code or error: ${e.message}",
                                        Toast.LENGTH_LONG
                                    ).show()
                                }
                                fetchAndUpdate { s ->
                                    status = s
                                    isConnected = true
                                    connectionText = "Online"
                                }
                            }
                        },
                        onDismissAlarm = {
                            Toast.makeText(
                                this@MainActivity,
                                "Use the PC app to dismiss alarms (admin required)",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    )

                    // UI-only polling for live display updates
                    LaunchedEffect(Unit) {
                        while (coroutineContext.isActive) {
                            val result = apiService.getStatus()
                            result.onSuccess { s ->
                                status = s
                                isConnected = true
                                connectionText = "Online"
                            }
                            result.onFailure {
                                isConnected = false
                                connectionText = if (status != null) "Offline" else "Cannot reach PC server"
                            }
                            delay(3000)
                        }
                    }
                }
            }
        }
    }

    override fun onStart() {
        super.onStart()
        PollingService.start(this)
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this, Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                return
            }
        }
        PollingService.start(this)
    }

    private suspend fun fetchAndUpdate(onUpdate: (StatusResponse) -> Unit) {
        val result = apiService.getStatus()
        result.onSuccess { s -> onUpdate(s) }
    }
}