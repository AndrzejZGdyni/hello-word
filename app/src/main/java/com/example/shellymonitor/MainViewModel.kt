package com.example.shellymonitor

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.shellymonitor.data.AppSettings
import com.example.shellymonitor.data.SettingsDataStore
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val dataStore = SettingsDataStore(app)

    val settings = dataStore.settings.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        AppSettings()
    )

    fun saveSettings(s: AppSettings) {
        viewModelScope.launch { dataStore.save(s) }
    }
}
