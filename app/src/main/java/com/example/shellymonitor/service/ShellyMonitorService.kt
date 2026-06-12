package com.example.shellymonitor.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import com.example.shellymonitor.data.ShellyCloudApi
import com.example.shellymonitor.data.SettingsDataStore
import com.example.shellymonitor.notification.NotificationHelper
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class ShellyMonitorService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var settingsDataStore: SettingsDataStore

    // Śledzi poprzedni stan, żeby powiadamiać tylko przy przejściu progu
    private var wasExporting = false

    override fun onCreate() {
        super.onCreate()
        settingsDataStore = SettingsDataStore(this)
        NotificationHelper.createChannels(this)
        startForeground(
            NotificationHelper.NOTIFICATION_ID_SERVICE,
            NotificationHelper.buildServiceNotification(this, "Uruchamianie…")
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        scope.launch { pollLoop() }
        return START_STICKY
    }

    private suspend fun pollLoop() {
        while (scope.isActive) {
            try {
                val settings = settingsDataStore.settings.first()

                if (settings.authKey.isBlank() || settings.deviceId.isBlank()) {
                    updateStatus("Brak konfiguracji — otwórz aplikację")
                    delay(10_000)
                    continue
                }

                val api = buildApi(settings.serverUrl)
                val response = api.getDeviceStatus(settings.authKey, settings.deviceId)

                val totalPower = response.data?.deviceStatus?.em?.totalActPower ?: 0.0
                val online = response.data?.online ?: false

                if (!online) {
                    updateStatus("Urządzenie offline")
                    wasExporting = false
                    delay(settings.pollIntervalSeconds * 1000L)
                    continue
                }

                updateStatus("Moc: %.1f W".format(totalPower))

                val isExporting = totalPower < settings.threshold
                if (isExporting && !wasExporting) {
                    NotificationHelper.sendExportAlert(this@ShellyMonitorService, totalPower, settings.threshold)
                }
                wasExporting = isExporting

                delay(settings.pollIntervalSeconds * 1000L)

            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                updateStatus("Błąd: ${e.message?.take(50)}")
                delay(15_000)
            }
        }
    }

    private fun updateStatus(text: String) {
        val manager = getSystemService(android.app.NotificationManager::class.java)
        manager.notify(
            NotificationHelper.NOTIFICATION_ID_SERVICE,
            NotificationHelper.buildServiceNotification(this, text)
        )
    }

    private fun buildApi(serverUrl: String): ShellyCloudApi =
        Retrofit.Builder()
            .baseUrl(serverUrl.trimEnd('/') + "/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ShellyCloudApi::class.java)

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        fun start(context: Context) =
            context.startForegroundService(Intent(context, ShellyMonitorService::class.java))

        fun stop(context: Context) =
            context.stopService(Intent(context, ShellyMonitorService::class.java))
    }
}
