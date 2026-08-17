package com.marco.pcrotationmanagerpro.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class ApiService(private val baseUrl: String = "http://192.168.1.100:6969") {

    fun updateBaseUrl(newUrl: String) {
        // Recreate with new URL - used for settings
    }

    private fun buildUrl(path: String): String {
        // Strip trailing slash from baseUrl
        val clean = baseUrl.trimEnd('/')
        val cleanPath = if (path.startsWith("/")) path else "/$path"
        return "$clean$cleanPath"
    }

    suspend fun getStatus(): Result<StatusResponse> = withContext(Dispatchers.IO) {
        try {
            val conn = URL(buildUrl("/status")).openConnection() as HttpURLConnection
            conn.connectTimeout = 5000
            conn.readTimeout = 5000
            conn.requestMethod = "GET"

            val code = conn.responseCode
            if (code != 200) {
                return@withContext Result.failure(Exception("Server returned $code"))
            }

            val reader = BufferedReader(InputStreamReader(conn.inputStream))
            val response = reader.readText()
            reader.close()
            conn.disconnect()

            val json = JSONObject(response)
            val status = StatusResponse(
                player1_time = json.optDouble("player1_time", 125.0),
                player2_time = json.optDouble("player2_time", 125.0),
                active_player = json.optInt("active_player", 1),
                stopwatch_mode = json.optBoolean("stopwatch_mode", false),
                stopwatch_minutes = json.optDouble("stopwatch_minutes", 0.0),
                break_tokens_p1 = json.optInt("break_tokens_p1", 2),
                break_tokens_p2 = json.optInt("break_tokens_p2", 2),
                on_break = json.optBoolean("on_break", false),
                break_player = if (json.has("break_player") && !json.isNull("break_player")) json.optInt("break_player") else null,
                break_reason = json.optString("break_reason", ""),
                alarm_active = json.optBoolean("alarm_active", false),
                player1_depleted = json.optBoolean("player1_depleted", false),
                player2_depleted = json.optBoolean("player2_depleted", false),
                unfair_break_approved = json.optBoolean("unfair_break_approved", false)
            )
            Result.success(status)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun stopPlayerBreak(secretCode: String): Result<BreakResponse> =
        withContext(Dispatchers.IO) {
            try {
                val conn = URL(buildUrl("/stop_player_break")).openConnection() as HttpURLConnection
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true

                val body = JSONObject().apply {
                    put("secret_code", secretCode)
                }

                val writer = OutputStreamWriter(conn.outputStream)
                writer.write(body.toString())
                writer.flush()
                writer.close()

                val code = conn.responseCode
                val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                val reader = BufferedReader(InputStreamReader(stream))
                val response = reader.readText()
                reader.close()
                conn.disconnect()

                val json = JSONObject(response)
                val ok = json.optBoolean("ok", false)
                val message = json.optString("message", "")
                Result.success(BreakResponse(ok, message))
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    suspend fun startPlayerBreak(reason: String, secretCode: String): Result<BreakResponse> =
        withContext(Dispatchers.IO) {
            try {
                val conn = URL(buildUrl("/start_player_break")).openConnection() as HttpURLConnection
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true

                val body = JSONObject().apply {
                    put("reason", reason)
                    put("secret_code", secretCode)
                }

                val writer = OutputStreamWriter(conn.outputStream)
                writer.write(body.toString())
                writer.flush()
                writer.close()

                val code = conn.responseCode
                val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                val reader = BufferedReader(InputStreamReader(stream))
                val response = reader.readText()
                reader.close()
                conn.disconnect()

                val json = JSONObject(response)
                val ok = json.optBoolean("ok", false)
                val message = json.optString("message", "")
                Result.success(BreakResponse(ok, message))
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    suspend fun checkHealth(): Result<HealthResponse> = withContext(Dispatchers.IO) {
        try {
            val conn = URL(buildUrl("/health")).openConnection() as HttpURLConnection
            conn.connectTimeout = 3000
            conn.readTimeout = 3000
            conn.requestMethod = "GET"

            val reader = BufferedReader(InputStreamReader(conn.inputStream))
            val response = reader.readText()
            reader.close()
            conn.disconnect()

            val json = JSONObject(response)
            Result.success(HealthResponse(json.optBoolean("ok"), json.optString("url")))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}