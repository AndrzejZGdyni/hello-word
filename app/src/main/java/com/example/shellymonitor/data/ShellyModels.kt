package com.example.shellymonitor.data

import com.google.gson.annotations.SerializedName

data class ShellyStatusResponse(
    val isok: Boolean,
    val data: ShellyResponseData?
)

data class ShellyResponseData(
    val online: Boolean,
    @SerializedName("device_status") val deviceStatus: DeviceStatus?
)

data class DeviceStatus(
    @SerializedName("em:0") val em: EmStatus?
)

data class EmStatus(
    @SerializedName("total_act_power") val totalActPower: Double = 0.0,
    @SerializedName("a_act_power") val aActPower: Double = 0.0,
    @SerializedName("b_act_power") val bActPower: Double = 0.0,
    @SerializedName("c_act_power") val cActPower: Double = 0.0
)
