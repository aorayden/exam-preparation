package com.college.mobile

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.college.mobile.models.Book
import java.util.Locale

class BooksAdapter : RecyclerView.Adapter<BooksAdapter.BookViewHolder>() {
    private var fullList = listOf<Book>()
    private val displayList = mutableListOf<Book>()

    fun setBooks(books: List<Book>) {
        fullList = books
        displayList.clear()
        displayList.addAll(books)
        notifyDataSetChanged()
    }

    fun filter(query: String) {
        val searchText = query.lowercase(Locale.getDefault()).trim()

        displayList.clear()

        if (searchText.isEmpty()) {
            displayList.addAll(fullList)
        } else {
            for (book in fullList) {
                if (book.name.lowercase(Locale.getDefault()).contains(searchText) ||
                    book.author.lowercase(Locale.getDefault()).contains(searchText) ||
                    book.code.lowercase(Locale.getDefault()).contains(searchText)) {
                    displayList.add(book)
                }
            }
        }
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): BookViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_book, parent, false)
        return BookViewHolder(view)
    }

    override fun onBindViewHolder(holder: BookViewHolder, position: Int) {
        holder.bind(displayList[position])
    }

    override fun getItemCount(): Int = displayList.size

    class BookViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvName: TextView = itemView.findViewById(R.id.tvBookName)
        private val tvAuthor: TextView = itemView.findViewById(R.id.tvBookAuthor)
        private val tvCode: TextView = itemView.findViewById(R.id.tvBookCode)
        private val tvYear: TextView = itemView.findViewById(R.id.tvBookYear)

        fun bind(book: Book) {
            tvName.text = book.name
            tvAuthor.text = "Автор: ${book.author}"
            tvCode.text = "Код: ${book.code}"
            tvYear.text = "${book.yearPublication} г."
        }
    }
}