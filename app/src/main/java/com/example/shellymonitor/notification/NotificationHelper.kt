package com.example.shellymonitor.notification

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import com.example.shellymonitor.MainActivity

object NotificationHelper {

    const val CHANNEL_SERVICE = "shelly_service"
    const val CHANNEL_ALERT = "shelly_alert"
    const val NOTIFICATION_ID_SERVICE = 1
    const val NOTIFICATION_ID_ALERT = 2

    fun createChannels(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_SERVICE,
                "Monitor działający w tle",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Stały status monitorowania Shelly"
            }
        )
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ALERT,
                "Alert: eksport energii",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Powiadomienie gdy moc < próg"
            }
        )
    }

    fun buildServiceNotification(context: Context, statusText: String): Notification {
        val intent = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(context, CHANNEL_SERVICE)
            .setContentTitle("Shelly Monitor")
            .setContentText(statusText)
            .setSmallIcon(android.R.drawable.ic_lock_idle_low_battery)
            .setContentIntent(intent)
            .setOngoing(true)
            .build()
    }

    fun sendExportAlert(context: Context, totalPower: Double, threshold: Float) {
        val manager = context.getSystemService(NotificationManager::class.java)
        val intent = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_ALERT)
            .setContentTitle("Eksport energii do sieci!")
            .setContentText("Moc chwilowa: %.1f W (próg: %.0f W)".format(totalPower, threshold))
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setContentIntent(intent)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        manager.notify(NOTIFICATION_ID_ALERT, notification)
    }
}
