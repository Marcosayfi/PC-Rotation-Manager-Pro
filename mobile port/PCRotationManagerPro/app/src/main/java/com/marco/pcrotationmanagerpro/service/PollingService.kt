package com.marco.pcrotationmanagerpro.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.marco.pcrotationmanagerpro.MainActivity
import com.marco.pcrotationmanagerpro.api.ApiService
import com.marco.pcrotationmanagerpro.notifications.NotificationHelper
import kotlinx.coroutines.*

class PollingService : Service() {

    companion object {
        private const val TAG = "PollingService"
        private const val FOREGROUND_CHANNEL_ID = "pc_rotation_polling"
        private const val FOREGROUND_NOTIFICATION_ID = 2001
        private const val POLL_INTERVAL_MS = 3000L

        fun start(context: Context) {
            val intent = Intent(context, PollingService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, PollingService::class.java))
        }
    }

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var apiService: ApiService
    private lateinit var notificationHelper: NotificationHelper
    private var lastAlarmActive = false
    private var lastActivePlayer = 0
    private var lastSwitchNotifiedPlayer = 0

    override fun onCreate() {
        super.onCreate()
        apiService = ApiService()
        notificationHelper = NotificationHelper(this)
        createForegroundChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(FOREGROUND_NOTIFICATION_ID, buildForegroundNotification("Monitoring PC timers..."))
        startPolling()
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }

    private fun createForegroundChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                FOREGROUND_CHANNEL_ID,
                "Background Polling",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps the app connected to the PC server for live notifications"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildForegroundNotification(text: String): Notification {
        val openIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, FOREGROUND_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_popup_sync)
            .setContentTitle("PC Rotation Manager")
            .setContentText(text)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    private fun updateForegroundNotification(text: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(FOREGROUND_NOTIFICATION_ID, buildForegroundNotification(text))
    }

    private fun startPolling() {
        serviceScope.launch {
            while (isActive) {
                try {
                    val result = apiService.getStatus()
                    result.onSuccess { status ->
                        val activePlayer = status.active_player

                        if (status.alarm_active && !lastAlarmActive) {
                            notificationHelper.sendTimeUpNotification(activePlayer)
                        }
                        if (!status.alarm_active && lastAlarmActive) {
                            notificationHelper.cancelNotification()
                        }

                        if (lastActivePlayer != 0 && activePlayer != lastActivePlayer && activePlayer != lastSwitchNotifiedPlayer) {
                            notificationHelper.sendPlayerSwitchNotification(activePlayer)
                            lastSwitchNotifiedPlayer = activePlayer
                        }

                        lastAlarmActive = status.alarm_active
                        lastActivePlayer = activePlayer

                        val p1 = formatMinutes(status.player1_time)
                        val p2 = formatMinutes(status.player2_time)
                        updateForegroundNotification("P1: $p1  |  P2: $p2  •  Active: Player $activePlayer")
                    }
                    result.onFailure {
                        updateForegroundNotification("PC server offline — retrying...")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Polling error", e)
                }
                delay(POLL_INTERVAL_MS)
            }
        }
    }

    private fun formatMinutes(minutes: Double): String {
        val totalSec = maxOf(0, kotlin.math.ceil(minutes * 60).toInt())
        val h = totalSec / 3600
        val m = (totalSec % 3600) / 60
        val s = totalSec % 60
        return if (h > 0) "$h:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}"
        else "${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}"
    }
}