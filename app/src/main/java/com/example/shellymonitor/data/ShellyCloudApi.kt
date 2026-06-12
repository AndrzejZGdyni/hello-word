package com.example.shellymonitor.data

import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST

interface ShellyCloudApi {
    @FormUrlEncoded
    @POST("device/status")
    suspend fun getDeviceStatus(
        @Field("auth_key") authKey: String,
        @Field("id") deviceId: String
    ): ShellyStatusResponse
}
