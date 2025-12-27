package com.college.mobile.api

import com.college.mobile.models.AuthRequest
import com.college.mobile.models.AuthResponse
import com.college.mobile.models.Book
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface APIService {
    // Авторизация.
    @POST("auth/login")
    fun login(@Body request: AuthRequest): Call<AuthResponse>

    // Получение книг читателя.
    @GET("tickets/{card_number}/books")
    fun getReaderBooks(@Path("card_number") cardNumber: Int): Call<List<Book>>
}

object RetrofitClient {
    private const val BASE_URL = "http://10.0.2.2:5079/"

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    val instance: APIService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(APIService::class.java)
    }
}