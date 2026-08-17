package com.marco.pcrotationmanagerpro.api

data class StatusResponse(
    val player1_time: Double,
    val player2_time: Double,
    val active_player: Int,
    val stopwatch_mode: Boolean,
    val stopwatch_minutes: Double,
    val break_tokens_p1: Int,
    val break_tokens_p2: Int,
    val on_break: Boolean,
    val break_player: Int? = null,
    val break_reason: String = "",
    val alarm_active: Boolean,
    val player1_depleted: Boolean = false,
    val player2_depleted: Boolean = false,
    val unfair_break_approved: Boolean = false
)

data class BreakResponse(
    val ok: Boolean,
    val message: String
)

data class HealthResponse(
    val ok: Boolean,
    val url: String
)