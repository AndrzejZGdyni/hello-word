package com.example.shellymonitor

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.example.shellymonitor.data.AppSettings
import com.example.shellymonitor.service.ShellyMonitorService
import com.example.shellymonitor.ui.theme.ShellyMonitorTheme

class MainActivity : ComponentActivity() {

    private val vm: MainViewModel by viewModels()

    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) {}

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNotificationPermission()
        setContent {
            ShellyMonitorTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val settings by vm.settings.collectAsState()
                    MonitorScreen(
                        settings = settings,
                        onSave = { vm.saveSettings(it) },
                        onStart = { ShellyMonitorService.start(this) },
                        onStop = { ShellyMonitorService.stop(this) }
                    )
                }
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}

@Composable
fun MonitorScreen(
    settings: AppSettings,
    onSave: (AppSettings) -> Unit,
    onStart: () -> Unit,
    onStop: () -> Unit
) {
    var serverUrl by remember(settings.serverUrl) { mutableStateOf(settings.serverUrl) }
    var authKey by remember(settings.authKey) { mutableStateOf(settings.authKey) }
    var deviceId by remember(settings.deviceId) { mutableStateOf(settings.deviceId) }
    var threshold by remember(settings.threshold) { mutableStateOf(settings.threshold.toString()) }
    var pollInterval by remember(settings.pollIntervalSeconds) { mutableStateOf(settings.pollIntervalSeconds.toString()) }
    var saved by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Shelly Pro 3EM Monitor", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Powiadomienie gdy suma mocy chwilowej < próg (eksport do sieci)",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        HorizontalDivider()

        OutlinedTextField(
            value = serverUrl,
            onValueChange = { serverUrl = it; saved = false },
            label = { Text("URL serwera Shelly Cloud") },
            placeholder = { Text("https://shelly-13-eu.shelly.cloud") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = authKey,
            onValueChange = { authKey = it; saved = false },
            label = { Text("Auth Key (z konta Shelly Cloud)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            visualTransformation = PasswordVisualTransformation()
        )

        OutlinedTextField(
            value = deviceId,
            onValueChange = { deviceId = it; saved = false },
            label = { Text("Device ID") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = threshold,
            onValueChange = { threshold = it; saved = false },
            label = { Text("Próg mocy [W]") },
            placeholder = { Text("-50") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )

        OutlinedTextField(
            value = pollInterval,
            onValueChange = { pollInterval = it; saved = false },
            label = { Text("Interwał odpytywania [sekundy]") },
            placeholder = { Text("30") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )

        Button(
            onClick = {
                onSave(
                    AppSettings(
                        serverUrl = serverUrl.trim().trimEnd('/'),
                        authKey = authKey.trim(),
                        deviceId = deviceId.trim(),
                        threshold = threshold.toFloatOrNull() ?: -50f,
                        pollIntervalSeconds = (pollInterval.toIntOrNull() ?: 30).coerceAtLeast(5)
                    )
                )
                saved = true
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (saved) "Zapisano ✓" else "Zapisz ustawienia")
        }

        HorizontalDivider()

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(onClick = onStart, modifier = Modifier.weight(1f)) {
                Text("▶ Start")
            }
            OutlinedButton(onClick = onStop, modifier = Modifier.weight(1f)) {
                Text("■ Stop")
            }
        }

        Text(
            "Po naciśnięciu Start serwis działa w tle — zobaczysz trwałe powiadomienie z aktualną mocą. " +
            "Alert zostanie wysłany tylko raz przy każdym przejściu poniżej progu.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(8.dp))

        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Jak znaleźć dane konfiguracyjne:", style = MaterialTheme.typography.labelLarge)
                Text("• Auth Key: Shelly Cloud → My Account → Security → Authorization cloud key", style = MaterialTheme.typography.bodySmall)
                Text("• Device ID: Shelly Cloud → urządzenie → Settings → Device information", style = MaterialTheme.typography.bodySmall)
                Text("• URL serwera: widoczny w Shelly Cloud (np. shelly-13-eu.shelly.cloud)", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
