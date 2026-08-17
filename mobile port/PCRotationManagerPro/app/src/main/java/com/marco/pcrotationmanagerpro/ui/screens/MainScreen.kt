package com.marco.pcrotationmanagerpro.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.marco.pcrotationmanagerpro.api.StatusResponse
import com.marco.pcrotationmanagerpro.ui.components.PlayerCard
import com.marco.pcrotationmanagerpro.ui.theme.*
import kotlin.math.ceil
import kotlin.math.max

object TimeFormatter {
    fun formatTime(minutes: Double): String {
        val totalSec = max(0.0, ceil(minutes * 60)).toInt()
        val h = totalSec / 3600
        val m = (totalSec % 3600) / 60
        val s = totalSec % 60
        return if (h > 0) {
            "${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}"
        } else {
            "${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}"
        }
    }

    fun formatFinishTime(minutes: Double): String {
        if (minutes <= 0) return "Time's up!"
        val millis = (minutes * 60 * 1000).toLong()
        val finishTime = java.util.Calendar.getInstance().apply {
            timeInMillis = timeInMillis + millis
        }
        val h = finishTime.get(java.util.Calendar.HOUR_OF_DAY)
        val m = finishTime.get(java.util.Calendar.MINUTE)
        return "Finishes at: ${h}:${m.toString().padStart(2, '0')}"
    }
}

@Composable
fun MainScreen(
    status: StatusResponse?,
    connectionStatus: String,
    isConnected: Boolean,
    showBreakDialog: Boolean,
    showStopBreakDialog: Boolean,
    onShowBreakDialog: () -> Unit,
    onDismissBreakDialog: () -> Unit,
    onStartBreak: (reason: String, secretCode: String) -> Unit,
    onShowStopBreakDialog: () -> Unit,
    onDismissStopBreakDialog: () -> Unit,
    onStopBreak: (secretCode: String) -> Unit,
    onDismissAlarm: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .verticalScroll(scrollState)
            .padding(16.dp)
    ) {
        // Header
        Text(
            text = "PC Rotation Manager Pro",
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = TextPrimary,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(2.dp))

        Text(
            text = connectionStatus,
            fontSize = 12.sp,
            color = if (isConnected) Player1Green else DangerRed,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Player Cards - stacked vertically (one by one)
        if (status != null) {
            val activePlayer = status.active_player
            val onBreak = status.on_break

            val p1Time = status.player1_time
            val p2Time = status.player2_time

            // Player 1 Card
            PlayerCard(
                title = "Player 1",
                color = Player1Green,
                timeText = TimeFormatter.formatTime(p1Time),
                finishText = TimeFormatter.formatFinishTime(p1Time),
                breakTokens = status.break_tokens_p1,
                isActive = activePlayer == 1 && !onBreak,
                isTimeLow = p1Time <= 5 || status.player1_depleted,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Player 2 Card
            PlayerCard(
                title = "Player 2",
                color = Player2Blue,
                timeText = TimeFormatter.formatTime(p2Time),
                finishText = TimeFormatter.formatFinishTime(p2Time),
                breakTokens = status.break_tokens_p2,
                isActive = activePlayer == 2 && !onBreak,
                isTimeLow = p2Time <= 5 || status.player2_depleted,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Status bar
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = DarkCard)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Active: Player ${status.active_player}",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )

                    Spacer(modifier = Modifier.height(4.dp))

                    val activeTime = if (activePlayer == 1) p1Time else p2Time
                    Text(
                        text = TimeFormatter.formatFinishTime(activeTime),
                        fontSize = 12.sp,
                        color = TextMuted
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    // Badges
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (onBreak) {
                            val unfair = if (status.unfair_break_approved) " (UNFAIR)" else ""
                            Badge(
                                containerColor = WarningYellow.copy(alpha = 0.2f),
                                contentColor = WarningYellow
                            ) {
                                Text(
                                    "On break: ${status.break_reason}$unfair",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }

                        if (status.stopwatch_mode) {
                            Badge(
                                containerColor = AccentOrange.copy(alpha = 0.2f),
                                contentColor = AccentOrange
                            ) {
                                Text(
                                    "Stopwatch ${TimeFormatter.formatTime(status.stopwatch_minutes)}",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }

                        if (status.alarm_active) {
                            Badge(
                                containerColor = DangerRed.copy(alpha = 0.27f),
                                contentColor = DangerRed
                            ) {
                                Text(
                                    "TIME UP",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }
                }
            }

            // Alarm banner
            if (status.alarm_active) {
                Spacer(modifier = Modifier.height(12.dp))

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(6.dp),
                    colors = CardDefaults.cardColors(containerColor = DangerRed)
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "⏰ TIME UP — Dismiss alarm to continue",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        Button(
                            onClick = onDismissAlarm,
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color.White,
                                contentColor = DangerRed
                            )
                        ) {
                            Text("Dismiss Alarm", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Break / Stop Break button
            if (onBreak) {
                Button(
                    onClick = onShowStopBreakDialog,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = WarningYellow,
                        contentColor = Color.Black
                    ),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        "Stop Break",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(vertical = 4.dp)
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = "Stopping or starting a break requires your secret code.",
                    fontSize = 11.sp,
                    color = TextMuted,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )
            } else {
                Button(
                    onClick = onShowBreakDialog,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AccentOrange,
                        contentColor = Color.White
                    ),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        "Start Break",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(vertical = 4.dp)
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = "Uses 1 break token. Requires your secret code.",
                    fontSize = 11.sp,
                    color = TextMuted,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Spacer pushes footer to bottom
        Spacer(modifier = Modifier.weight(1f))

        // Footer
        Text(
            text = "PC Rotation Manager Pro v1.0",
            fontSize = 11.sp,
            color = TextMuted,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center
        )
    }

    // Break dialogs
    if (showBreakDialog) {
        BreakDialog(
            onDismiss = onDismissBreakDialog,
            onStartBreak = onStartBreak
        )
    }

    if (showStopBreakDialog) {
        StopBreakDialog(
            onDismiss = onDismissStopBreakDialog,
            onStopBreak = onStopBreak
        )
    }
}

@Composable
fun StopBreakDialog(
    onDismiss: () -> Unit,
    onStopBreak: (secretCode: String) -> Unit
) {
    var secretCode by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = DarkCard)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Stop Break",
                    style = MaterialTheme.typography.headlineSmall,
                    color = TextPrimary
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "Enter your secret code to end the break",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextMuted
                )

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = secretCode,
                    onValueChange = { secretCode = it; error = null },
                    label = { Text("Your secret code") },
                    placeholder = { Text("Active player's secret code") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = WarningYellow,
                        unfocusedBorderColor = Color(0xFF444444),
                        focusedLabelColor = WarningYellow,
                        cursorColor = TextPrimary,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary
                    )
                )

                if (error != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = error!!,
                        color = DangerRed,
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = TextMuted),
                        border = ButtonDefaults.outlinedButtonBorder.copy(
                            brush = androidx.compose.ui.graphics.SolidColor(Color(0xFF444444))
                        )
                    ) {
                        Text("Cancel")
                    }

                    Button(
                        onClick = {
                            if (secretCode.isBlank()) {
                                error = "Please enter your secret code"
                                return@Button
                            }
                            isLoading = true
                            onStopBreak(secretCode.trim())
                        },
                        modifier = Modifier.weight(1f),
                        enabled = !isLoading,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = WarningYellow,
                            contentColor = Color.Black
                        )
                    ) {
                        if (isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = Color.Black,
                                strokeWidth = 2.dp
                            )
                        } else {
                            Text("Stop Break")
                        }
                    }
                }
            }
        }
    }
}