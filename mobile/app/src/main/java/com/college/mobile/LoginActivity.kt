package com.college.mobile

import android.content.Intent
import android.os.Bundle
import android.widget.EditText
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.AppCompatButton
import com.college.mobile.api.RetrofitClient
import com.college.mobile.models.AuthRequest
import com.college.mobile.models.AuthResponse
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_login)

        val etCardNumber = findViewById<EditText>(R.id.etCardNumber)
        val btnLogin = findViewById<AppCompatButton>(R.id.btnLogin)

        btnLogin.setOnClickListener {
            val cardNumberText = etCardNumber.text.toString().trim()

            if (cardNumberText.isEmpty()) {
                Toast.makeText(this, "Пожалуйста, заполните поле.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val cardNumber = cardNumberText.toIntOrNull()

            if (cardNumber == null) {
                Toast.makeText(this, "Некорректный номер билета.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val request = AuthRequest(cardNumber)

            RetrofitClient.instance.login(request).enqueue(object : Callback<AuthResponse> {
                override fun onResponse(call: Call<AuthResponse>, response: Response<AuthResponse>) {
                    if (response.isSuccessful && response.body() != null) {
                        val authResponse = response.body()!!
                        if (authResponse.success && authResponse.user?.role == "Читатель") {
                            Toast.makeText(applicationContext, "Добро пожаловать, ${authResponse.user?.name} ${authResponse.user?.patronymic}!", Toast.LENGTH_SHORT).show()
                            val intent = Intent(this@LoginActivity, MainActivity::class.java)
                            intent.putExtra("CARD_NUMBER", authResponse.user?.cardNumber)
                            startActivity(intent)
                            finish()
                        } else if (authResponse.success && authResponse.user?.role == "Администратор") {
                            Toast.makeText(applicationContext, "Администратор не может пользоваться клиентским приложением.", Toast.LENGTH_SHORT).show()
                        } else {
                            Toast.makeText(applicationContext, authResponse.message, Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        handleError(response)
                    }
                }

                override fun onFailure(call: Call<AuthResponse>, t: Throwable) {
                    Toast.makeText(applicationContext, "Ошибка сети: ${t.localizedMessage}.", Toast.LENGTH_SHORT).show()
                }
            })
        }
    }

    private fun handleError(response: Response<AuthResponse>) {
        try {
            val errorJson = response.errorBody()?.string()
            if (errorJson != null) {
                val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
                val adapter = moshi.adapter(AuthResponse::class.java)
                val errorResponse = adapter.fromJson(errorJson)
                Toast.makeText(applicationContext, errorResponse?.message ?: "Произошла ошибка сервера.", Toast.LENGTH_LONG).show()
            } else {
                Toast.makeText(applicationContext, "Ошибка сервера: ${response.code()}.", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            Toast.makeText(applicationContext, "Ошибка чтения ответа сервера.", Toast.LENGTH_LONG).show()
        }
    }
}