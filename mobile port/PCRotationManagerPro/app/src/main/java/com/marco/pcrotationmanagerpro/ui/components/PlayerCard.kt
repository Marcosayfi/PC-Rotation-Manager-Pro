package com.marco.pcrotationmanagerpro.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.marco.pcrotationmanagerpro.ui.theme.*

@Composable
fun PlayerCard(
    title: String,
    color: Color,
    timeText: String,
    finishText: String,
    breakTokens: Int,
    maxBreakTokens: Int = 2,
    isActive: Boolean,
    isTimeLow: Boolean = false,
    modifier: Modifier = Modifier
) {
    val borderColor = if (isActive) color else Color(0xFF444444)
    val borderWidth = if (isActive) 3.dp else 2.dp
    val bgColor = if (isActive) DarkSurface else DarkCard
    val timerColor = if (isTimeLow) TimerLow else TimerNormal

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(bgColor)
            .border(borderWidth, borderColor, RoundedCornerShape(12.dp))
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            color = color
        )

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = timeText,
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            color = timerColor,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(2.dp))

        Text(
            text = finishText,
            fontSize = 10.sp,
            color = TextDim,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = "Break tokens: $breakTokens/$maxBreakTokens",
            fontSize = 12.sp,
            color = TextMuted
        )

        Spacer(modifier = Modifier.height(4.dp))

        LinearProgressIndicator(
            progress = { breakTokens.toFloat() / maxBreakTokens.toFloat() },
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp)),
            color = color,
            trackColor = Color(0xFF333333),
        )
    }
}