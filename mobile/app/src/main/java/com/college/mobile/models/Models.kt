package com.college.mobile.models

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

// Ответ авторизации.
@JsonClass(generateAdapter = true)
data class AuthResponse(
    @Json(name = "success") val success: Boolean,
    @Json(name = "message") val message: String,
    @Json(name = "user") val user: UserData? = null,
)

// Данные читателя.
@JsonClass(generateAdapter = true)
data class UserData(
    @Json(name = "card_number") val cardNumber: Int,
    @Json(name = "name") val name: String,
    @Json(name = "patronymic") val patronymic: String,
    @Json(name = "role") val role: String,
)

// Запрос авторизации.
@JsonClass(generateAdapter = true)
data class AuthRequest(
    @Json(name = "card_number") val cardNumber: Int,
)

// ------

@JsonClass(generateAdapter = true)
data class Book(
    @Json(name = "code") val code: String,
    @Json(name = "author") val author: String,
    @Json(name = "name") val name: String,
    @Json(name = "year_publication") val yearPublication: Int,
    @Json(name = "sign_novelty_and_annotations") val signNoveltyAndAnnotations: String,
)