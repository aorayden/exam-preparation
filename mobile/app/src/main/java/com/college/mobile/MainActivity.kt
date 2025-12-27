package com.college.mobile

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.college.mobile.api.RetrofitClient
import com.college.mobile.models.Book
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class MainActivity : AppCompatActivity() {

    private lateinit var adapter: BooksAdapter
    private lateinit var progressBar: ProgressBar
    private lateinit var tvEmpty: TextView
    private lateinit var recyclerView: RecyclerView
    private lateinit var etSearch: EditText
    private lateinit var btnRefresh: ImageButton

    private var currentCardNumber: Int = -1

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        progressBar = findViewById(R.id.progressBar)
        tvEmpty = findViewById(R.id.tvEmpty)
        recyclerView = findViewById(R.id.recyclerViewBooks)
        etSearch = findViewById(R.id.etSearch)
        btnRefresh = findViewById(R.id.btnRefresh)

        recyclerView.layoutManager = LinearLayoutManager(this)
        adapter = BooksAdapter()
        recyclerView.adapter = adapter

        currentCardNumber = intent.getIntExtra("CARD_NUMBER", -1)

        if (currentCardNumber != -1) {
            loadBooks()
        } else {
            Toast.makeText(this, "Ошибка: неверный ID пользователя.", Toast.LENGTH_SHORT).show()
        }

        btnRefresh.setOnClickListener {
            etSearch.text.clear()
            loadBooks()
        }

        etSearch.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}

            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                adapter.filter(s.toString())
            }

            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun loadBooks() {
        if (currentCardNumber == -1) return

        progressBar.visibility = View.VISIBLE
        recyclerView.visibility = View.INVISIBLE
        tvEmpty.visibility = View.GONE

        RetrofitClient.instance.getReaderBooks(currentCardNumber).enqueue(object : Callback<List<Book>> {
            override fun onResponse(call: Call<List<Book>>, response: Response<List<Book>>) {
                progressBar.visibility = View.GONE

                if (response.isSuccessful) {
                    val books = response.body() ?: emptyList()

                    adapter.setBooks(books)

                    if (books.isNotEmpty()) {
                        recyclerView.visibility = View.VISIBLE
                    } else {
                        tvEmpty.visibility = View.VISIBLE
                    }
                } else {
                    Toast.makeText(applicationContext, "Ошибка сервера: ${response.code()}.", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<List<Book>>, t: Throwable) {
                progressBar.visibility = View.GONE
                recyclerView.visibility = View.VISIBLE
                Toast.makeText(applicationContext, "Нет связи с сервером.", Toast.LENGTH_LONG).show()
            }
        })
    }
}