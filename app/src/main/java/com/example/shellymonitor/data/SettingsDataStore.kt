package com.example.shellymonitor.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

data class AppSettings(
    val serverUrl: String = "https://shelly-13-eu.shelly.cloud",
    val authKey: String = "",
    val deviceId: String = "",
    val threshold: Float = -50f,
    val pollIntervalSeconds: Int = 30
)

class SettingsDataStore(private val context: Context) {

    companion object {
        val SERVER_URL = stringPreferencesKey("server_url")
        val AUTH_KEY = stringPreferencesKey("auth_key")
        val DEVICE_ID = stringPreferencesKey("device_id")
        val THRESHOLD = floatPreferencesKey("threshold")
        val POLL_INTERVAL = intPreferencesKey("poll_interval")
    }

    val settings: Flow<AppSettings> = context.dataStore.data.map { prefs ->
        AppSettings(
            serverUrl = prefs[SERVER_URL] ?: "https://shelly-13-eu.shelly.cloud",
            authKey = prefs[AUTH_KEY] ?: "",
            deviceId = prefs[DEVICE_ID] ?: "",
            threshold = prefs[THRESHOLD] ?: -50f,
            pollIntervalSeconds = prefs[POLL_INTERVAL] ?: 30
        )
    }

    suspend fun save(settings: AppSettings) {
        context.dataStore.edit { prefs ->
            prefs[SERVER_URL] = settings.serverUrl
            prefs[AUTH_KEY] = settings.authKey
            prefs[DEVICE_ID] = settings.deviceId
            prefs[THRESHOLD] = settings.threshold
            prefs[POLL_INTERVAL] = settings.pollIntervalSeconds
        }
    }
}
