import sys
import httpx
import asyncio
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSlot, QDate
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QMainWindow, QHBoxLayout,
                             QTableWidget, QHeaderView, QAbstractItemView, QFormLayout, QFrame, QSpinBox, QDateEdit)
from qasync import QEventLoop

# ======
# API сервис
# ======

class APIService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(APIService, cls).__new__(cls, *args, **kwargs)
            cls._instance.client = None
            cls._instance.base_url = 'http://127.0.0.1:5079'
        return cls._instance

    # ===
    # Функции жизненного цикла
    # ===
    async def init_session(self):
        if self.client is None:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0, trust_env=False)

    async def close_session(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    # ===
    # Базовые функции (GET / POST)
    # ===
    async def _get(self, endpoint, params=None):
        if not self.client:
            await self.init_session()
        try:
            response = await self.client.get(endpoint, params=params)
            return response.json()
        except Exception:
            return []

    async def _post(self, endpoint, payload):
        if not self.client:
            await self.init_session()
        try:
            response = await self.client.post(endpoint, json=payload)
            return response.json()
        except Exception as exception:
            return {'success': False, 'message': str(exception)}

    # ===
    # Запросы
    # ===

    async def login(self, login, password):
        return await self._post('auth/login', {'login': login, 'password': password})

    async def get_all_readers(self):
        # Используем новый эндпоинт, который мы добавили в server.py
        return await self._get('readers')

    async def register_user(self, payload):
        # Используем существующий метод регистрации
        return await self._post('auth/register', payload)

    async def get_all_books(self):
        return await self._get('books')

    async def add_book(self, payload):
        return await self._post('books/add', payload)

    async def get_available_books(self):
        return await self._get('books/available')

    async def create_ticket(self, payload):
        return await self._post('tickets/create', payload)

api_service = APIService()

# ======
# Окно оформления чит. дневника.
# ======

class TicketWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Оформление выдачи книг')
        self.resize(1200, 800)

        # Данные
        self.all_readers = []
        self.available_books_source = []  # Все свободные, загруженные с сервера
        self.current_available_books = []  # Те, что отображаются слева
        self.selected_books = []  # Те, что отображаются справа (выбранные)

        self.selected_reader_id = None  # ID выбранного читателя

        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        # Основной вертикальный слой
        main_layout = QVBoxLayout(self)

        # === 1. БЛОК ЧИТАТЕЛЕЙ (ВЕРХ) ===
        readers_group = QWidget()
        readers_layout = QVBoxLayout(readers_group)
        readers_layout.setContentsMargins(0, 0, 0, 0)

        lbl_r = QLabel("1. Выберите читателя:")
        lbl_r.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        readers_layout.addWidget(lbl_r)

        self.reader_search = QLineEdit()
        self.reader_search.setPlaceholderText("Поиск читателя...")
        self.reader_search.textChanged.connect(self.filter_readers)
        readers_layout.addWidget(self.reader_search)

        self.table_readers = QTableWidget()
        self.table_readers.setColumnCount(4)
        self.table_readers.setHorizontalHeaderLabels(['№', 'Фамилия', 'Имя', 'Телефон'])
        self.table_readers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_readers.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_readers.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_readers.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_readers.setMaximumHeight(200)  # Чтобы не занимала весь экран
        # Событие клика по строке
        self.table_readers.itemClicked.connect(self.on_reader_clicked)
        readers_layout.addWidget(self.table_readers)

        main_layout.addWidget(readers_group)

        # Разделитель
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(line1)

        # === 2. БЛОК КНИГ (СЕРЕДИНА) ===
        lbl_b = QLabel("2. Выберите книги:")
        lbl_b.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        main_layout.addWidget(lbl_b)

        books_container = QHBoxLayout()

        # -- Левая таблица (Доступные) --
        left_box = QVBoxLayout()
        lbl_av = QLabel("Доступные книги")
        self.input_search_book = QLineEdit()
        self.input_search_book.setPlaceholderText("Поиск книги...")
        self.input_search_book.textChanged.connect(self.filter_available_books)

        self.table_available = QTableWidget()
        self.table_available.setColumnCount(3)
        self.table_available.setHorizontalHeaderLabels(['Код', 'Название', 'Автор'])
        self.table_available.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_available.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_available.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        left_box.addWidget(lbl_av)
        left_box.addWidget(self.input_search_book)
        left_box.addWidget(self.table_available)

        # -- Центральные кнопки --
        center_box = QVBoxLayout()
        center_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_to_right = QPushButton(">>>")
        btn_to_right.setFixedSize(50, 50)
        btn_to_right.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold;")
        btn_to_right.clicked.connect(self.move_to_selected)

        btn_to_left = QPushButton("<<<")
        btn_to_left.setFixedSize(50, 50)
        btn_to_left.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        btn_to_left.clicked.connect(self.move_to_available)

        center_box.addWidget(btn_to_right)
        center_box.addSpacing(20)
        center_box.addWidget(btn_to_left)

        # -- Правая таблица (Выбранные) --
        right_box = QVBoxLayout()
        lbl_sel = QLabel("Выбранные к выдаче")

        self.table_selected = QTableWidget()
        self.table_selected.setColumnCount(3)
        self.table_selected.setHorizontalHeaderLabels(['Код', 'Название', 'Автор'])
        self.table_selected.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_selected.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_selected.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        right_box.addWidget(lbl_sel)
        right_box.addWidget(self.table_selected)

        # Добавляем в горизонтальный слой
        books_container.addLayout(left_box, 45)
        books_container.addLayout(center_box, 10)
        books_container.addLayout(right_box, 45)

        main_layout.addLayout(books_container)

        # === 3. БЛОК ОФОРМЛЕНИЯ (НИЗ) ===
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(line2)

        bottom_panel = QHBoxLayout()

        lbl_date = QLabel("Дата возврата:")
        self.date_return = QDateEdit()
        self.date_return.setCalendarPopup(True)
        self.date_return.setDate(QDate.currentDate().addDays(7))  # По умолчанию +неделя
        self.date_return.setMinimumDate(QDate.currentDate())

        self.btn_confirm = QPushButton("ОФОРМИТЬ ВЫДАЧУ")
        self.btn_confirm.setMinimumHeight(40)
        self.btn_confirm.setStyleSheet("background-color: #198754; color: white; font-weight: bold; font-size: 14px;")
        self.btn_confirm.clicked.connect(self.submit_ticket)

        bottom_panel.addWidget(lbl_date)
        bottom_panel.addWidget(self.date_return)
        bottom_panel.addStretch()
        bottom_panel.addWidget(self.btn_confirm)

        main_layout.addLayout(bottom_panel)

    # --- ЛОГИКА ЗАГРУЗКИ ---

    def refresh_data(self):
        asyncio.create_task(self.load_all())

    async def load_all(self):
        # 1. Читатели
        readers = await api_service.get_all_readers()
        if isinstance(readers, list):
            self.all_readers = readers
            self.filter_readers()

        # 2. Книги (только свободные)
        books = await api_service.get_available_books()
        if isinstance(books, list):
            self.available_books_source = books
            self.current_available_books = list(self.available_books_source)  # Копия
            self.selected_books = []
            self.update_books_tables()

    # --- ЛОГИКА ЧИТАТЕЛЕЙ ---

    def filter_readers(self):
        text = self.reader_search.text().lower().strip()

        self.table_readers.setRowCount(0)
        from PyQt6.QtWidgets import QTableWidgetItem

        for r in self.all_readers:
            if text and (text not in r['surname'].lower()):
                continue

            row = self.table_readers.rowCount()
            self.table_readers.insertRow(row)

            # Скрываем ID в UserRole или просто используем колонку 0
            self.table_readers.setItem(row, 0, QTableWidgetItem(str(r['card_number'])))
            self.table_readers.setItem(row, 1, QTableWidgetItem(r['surname']))
            self.table_readers.setItem(row, 2, QTableWidgetItem(r['name']))
            self.table_readers.setItem(row, 3, QTableWidgetItem(r['phone']))

    def on_reader_clicked(self, item):
        row = item.row()
        # Номер билета у нас в 0-й колонке
        card_num_str = self.table_readers.item(row, 0).text()
        self.selected_reader_id = int(card_num_str)
        # Для визуального подтверждения можно подсветить, но Qt и так выделяет

    # --- ЛОГИКА КНИГ (ПЕРЕНОС) ---

    def filter_available_books(self):
        # Фильтрация только левой таблицы, учитывая что книги могут быть уже справа
        text = self.input_search_book.text().lower().strip()

        filtered = []
        for b in self.current_available_books:
            if not text or (text in b['name'].lower() or text in b['code'].lower()):
                filtered.append(b)

        self.populate_table(self.table_available, filtered)

    def update_books_tables(self):
        # Обновляет обе таблицы на основе списков self.current_available_books и self.selected_books
        self.filter_available_books()  # Обновит левую с учетом поиска
        self.populate_table(self.table_selected, self.selected_books)

    def populate_table(self, table, data_list):
        from PyQt6.QtWidgets import QTableWidgetItem
        table.setRowCount(0)
        for b in data_list:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(b['code']))
            table.setItem(row, 1, QTableWidgetItem(b['name']))
            table.setItem(row, 2, QTableWidgetItem(b['author']))
            # Храним полный объект книги в скрытых данных первой ячейки, чтобы удобно доставать
            table.item(row, 0).setData(Qt.ItemDataRole.UserRole, b)

    def move_to_selected(self):
        # 1. Получаем выбранные строки слева
        rows = sorted(set(index.row() for index in self.table_available.selectedIndexes()), reverse=True)
        if not rows: return

        for row in rows:
            # Достаем объект книги
            book_item = self.table_available.item(row, 0)
            # В filter_available_books мы не сохраняли объект в UserRole (упростили),
            # поэтому найдем по коду.
            code = book_item.text()

            # Ищем в списке current_available_books
            book_obj = next((b for b in self.current_available_books if b['code'] == code), None)

            if book_obj:
                self.current_available_books.remove(book_obj)
                self.selected_books.append(book_obj)

        self.update_books_tables()

    def move_to_available(self):
        # 1. Получаем выбранные строки справа
        rows = sorted(set(index.row() for index in self.table_selected.selectedIndexes()), reverse=True)
        if not rows: return

        for row in rows:
            code = self.table_selected.item(row, 0).text()
            book_obj = next((b for b in self.selected_books if b['code'] == code), None)

            if book_obj:
                self.selected_books.remove(book_obj)
                self.current_available_books.append(book_obj)

        self.update_books_tables()

    # --- ОТПРАВКА ---

    def submit_ticket(self):
        if not self.selected_reader_id:
            QMessageBox.warning(self, "Ошибка", "Выберите читателя!")
            return

        if not self.selected_books:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну книгу!")
            return

        book_codes = [b['code'] for b in self.selected_books]

        # Формируем JSON
        payload = {
            "reader_card_number": self.selected_reader_id,
            "books": book_codes,
            "date_issue": datetime.now().strftime("%d.%m.%Y"),
            "date_return": self.date_return.date().toString("dd.MM.yyyy")
        }

        asyncio.create_task(self.process_submit(payload))

    async def process_submit(self, payload):
        res = await api_service.create_ticket(payload)

        if res.get('success'):
            QMessageBox.information(self, "Успех", "Книги успешно выданы!")
            self.close()  # Закрываем окно
        else:
            QMessageBox.critical(self, "Ошибка", res.get('message', 'Error'))

# ======
# Окно управления книгами.
# ======

class BooksWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Управление книжным фондом')
        self.resize(1100, 600)
        self.all_books = []
        self.filtered_books = []
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_panel.setFixedWidth(320)

        title_label = QLabel("Новая книга")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        left_layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)

        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("ISBN-0000")

        self.input_author = QLineEdit()
        self.input_author.setPlaceholderText("Фамилия И.О.")

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Название книги")

        self.input_year = QSpinBox()
        self.input_year.setRange(1900, 2100)
        self.input_year.setValue(2025)
        self.input_year.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        self.input_notes = QLineEdit()
        self.input_notes.setPlaceholderText("Новизна / Аннотация")

        form_layout.addRow("Код (ISBN):", self.input_code)
        form_layout.addRow("Автор:", self.input_author)
        form_layout.addRow("Название:", self.input_name)
        form_layout.addRow("Год изд.:", self.input_year)
        form_layout.addRow("Пометки:", self.input_notes)

        left_layout.addLayout(form_layout)

        self.add_btn = QPushButton("Добавить книгу")
        self.add_btn.setStyleSheet(
            "background-color: #198754; color: white; padding: 10px; font-weight: bold; margin-top: 10px;")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.on_add_click)
        left_layout.addWidget(self.add_btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Поиск по названию или коду...')
        self.search_input.textChanged.connect(self.apply_filter)
        right_layout.addWidget(self.search_input)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Код', 'Автор', 'Название', 'Год', 'Аннотация'])

        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Название тянется
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Код по размеру

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.table)

        btn_refresh = QPushButton("Обновить список")
        btn_refresh.clicked.connect(self.refresh_data)
        right_layout.addWidget(btn_refresh)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(line)
        main_layout.addWidget(right_panel)

    def refresh_data(self):
        asyncio.create_task(self.load_books())

    async def load_books(self):
        data = await api_service.get_all_books()
        if isinstance(data, dict) and 'message' in data:
            return
        self.all_books = data
        self.apply_filter()

    def apply_filter(self):
        text = self.search_input.text().lower().strip()
        self.filtered_books = []
        for b in self.all_books:
            b_name = b.get('name', '').lower()
            b_code = b.get('code', '').lower()
            if not text or text in b_name or text in b_code:
                self.filtered_books.append(b)
        self.populate_table()

    def populate_table(self):
        from PyQt6.QtWidgets import QTableWidgetItem
        self.table.setRowCount(0)
        for b in self.filtered_books:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(b.get('code', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(b.get('author', ''))))
            self.table.setItem(row, 2, QTableWidgetItem(str(b.get('name', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(str(b.get('year_publication', ''))))
            self.table.setItem(row, 4, QTableWidgetItem(str(b.get('sign_novelty_and_annotations', ''))))

    def on_add_click(self):
        payload = {
            "code": self.input_code.text().strip(),
            "author": self.input_author.text().strip(),
            "name": self.input_name.text().strip(),
            "year_publication": self.input_year.value(),
            "sign_novelty_and_annotations": self.input_notes.text().strip()
        }

        if not payload['code'] or not payload['name'] or not payload['author']:
            QMessageBox.warning(self, "Внимание", "Поля Код, Автор и Название обязательны!")
            return

        asyncio.create_task(self.process_add(payload))

    async def process_add(self, payload):
        self.add_btn.setEnabled(False)
        self.add_btn.setText("Сохранение...")

        res = await api_service.add_book(payload)

        self.add_btn.setEnabled(True)
        self.add_btn.setText("Добавить книгу")

        if res.get('success'):
            QMessageBox.information(self, "Успех", "Книга успешно добавлена!")
            self.input_code.clear()
            self.input_name.clear()
            self.input_author.clear()
            self.input_notes.clear()
            self.refresh_data()
        else:
            QMessageBox.critical(self, "Ошибка", res.get('message', 'Error'))

# ======
# Окно управления читателями.
# ======

class ReadersWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Управление читателями')
        self.resize(1000, 600)
        self.all_readers = []
        self.filtered_readers = []
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_panel.setFixedWidth(300)

        title_label = QLabel("Новый читатель")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        left_layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)

        self.input_surname = QLineEdit()
        self.input_surname.setPlaceholderText("Иванов")

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Иван")

        self.input_patronymic = QLineEdit()
        self.input_patronymic.setPlaceholderText("Иванович")

        self.input_address = QLineEdit()
        self.input_address.setPlaceholderText("ул. Ленина, д. 1")

        self.input_phone = QLineEdit()
        self.input_phone.setPlaceholderText("+7...")

        form_layout.addRow("Фамилия:", self.input_surname)
        form_layout.addRow("Имя:", self.input_name)
        form_layout.addRow("Отчество:", self.input_patronymic)
        form_layout.addRow("Адрес:", self.input_address)
        form_layout.addRow("Телефон:", self.input_phone)

        left_layout.addLayout(form_layout)

        self.add_btn = QPushButton("Добавить читателя")
        self.add_btn.setStyleSheet(
            "background-color: #198754; color: white; padding: 10px; font-weight: bold; margin-top: 10px;")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.on_add_click)
        left_layout.addWidget(self.add_btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Поиск по фамилии или номеру билета..')
        self.search_input.textChanged.connect(self.apply_filter)
        right_layout.addWidget(self.search_input)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['№ Билета', 'Фамилия', 'Имя', 'Отчество', 'Адрес', 'Телефон'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # Растягиваем все колонки
        self.table.horizontalHeader().setSectionResizeMode(0,
                                                           QHeaderView.ResizeMode.ResizeToContents)  # А номер билета по контенту
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.table)

        refresh_btn = QPushButton("Обновить таблицу")
        refresh_btn.clicked.connect(self.refresh_data)
        right_layout.addWidget(refresh_btn)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(line)
        main_layout.addWidget(right_panel)

    def refresh_data(self):
        asyncio.create_task(self.load_readers())

    async def load_readers(self):
        data = await api_service.get_all_readers()

        if isinstance(data, dict) and 'message' in data:
            QMessageBox.warning(self, 'Ошибка', data.get('message', 'Error'))
            return

        self.all_readers = data
        self.apply_filter()

    def apply_filter(self):
        search_text = self.search_input.text().lower().strip()

        self.filtered_readers = []
        for reader in self.all_readers:
            r_surname = str(reader.get('surname', '')).lower()
            r_card = str(reader.get('card_number', ''))

            if not search_text or search_text in r_surname or search_text in r_card:
                self.filtered_readers.append(reader)

        self.populate_table()

    def populate_table(self):
        from PyQt6.QtWidgets import QTableWidgetItem

        self.table.setRowCount(0)
        for reader in self.filtered_readers:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(reader.get('card_number', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(reader.get('surname', ''))))
            self.table.setItem(row, 2, QTableWidgetItem(str(reader.get('name', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(str(reader.get('patronymic', ''))))
            self.table.setItem(row, 4, QTableWidgetItem(str(reader.get('address', ''))))
            self.table.setItem(row, 5, QTableWidgetItem(str(reader.get('phone', ''))))

    def on_add_click(self):
        payload = {
            "surname": self.input_surname.text().strip(),
            "name": self.input_name.text().strip(),
            "patronymic": self.input_patronymic.text().strip(),
            "address": self.input_address.text().strip(),
            "phone": self.input_phone.text().strip(),
            "role": "Читатель"
        }

        if not payload["surname"] or not payload["name"] or not payload["phone"]:
            QMessageBox.warning(self, "Ошибка", "Поля `Фамилия`, `Имя` и `Телефон` обязательны для заполнения!")
            return

        asyncio.create_task(self.process_add_reader(payload))

    async def process_add_reader(self, payload):
        self.add_btn.setEnabled(False)
        self.add_btn.setText("Сохранение..")

        result = await api_service.register_user(payload)

        self.add_btn.setEnabled(True)
        self.add_btn.setText("Добавить читателя")

        if result.get('success'):
            QMessageBox.information(self, "Успех", f"Читатель добавлен!\nНомер билета: {result['user']['card_number']}")
            self.input_surname.clear()
            self.input_name.clear()
            self.input_patronymic.clear()
            self.input_address.clear()
            self.input_phone.clear()
            self.refresh_data()
        else:
            QMessageBox.critical(self, "Ошибка", result.get('message', 'Неизвестная ошибка'))

# ======
# Главное окно
# ======

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Система управления библиотекой')
        self.resize(800, 600)
        self.login_window = None
        self.modules = []
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)

        welcome_label = QLabel('Добро пожаловать в систему!')
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setFont(QFont('Arial', 20, QFont.Weight.Bold))
        layout.addWidget(welcome_label)

        readers_control_button = QPushButton('Управление читателями')
        readers_control_button.setFont(QFont('Arial', 12))
        readers_control_button.setCursor(Qt.CursorShape.PointingHandCursor)
        readers_control_button.setStyleSheet(
            f"QPushButton {{ background-color: {'#0d6efd'}; color: white; padding: 15px; border-radius: 8px; font-weight: bold; }} QPushButton:hover {{ opacity: 0.8; }}")
        readers_control_button.clicked.connect(self.open_readers_module)
        layout.addWidget(readers_control_button)

        books_control_button = QPushButton('Управление книгами')
        books_control_button.setFont(QFont('Arial', 12))
        books_control_button.setCursor(Qt.CursorShape.PointingHandCursor)
        books_control_button.setStyleSheet(
            f"QPushButton {{ background-color: {'#198754'}; color: white; padding: 15px; border-radius: 8px; font-weight: bold; }} QPushButton:hover {{ opacity: 0.8; }}")
        books_control_button.clicked.connect(self.open_books_module)
        layout.addWidget(books_control_button)

        registration_ticket_button = QPushButton('Оформление чит. дневника')
        registration_ticket_button.setFont(QFont('Arial', 12))
        registration_ticket_button.setCursor(Qt.CursorShape.PointingHandCursor)
        registration_ticket_button.setStyleSheet(
            f"QPushButton {{ background-color: {'#dc3545'}; color: white; padding: 15px; border-radius: 8px; font-weight: bold; }} QPushButton:hover {{ opacity: 0.8; }}")
        registration_ticket_button.clicked.connect(self.open_registration_ticket_module)
        layout.addWidget(registration_ticket_button)

        layout.addStretch()

        exit_button = QPushButton('Выход из системы')
        exit_button.setStyleSheet("padding: 10px; color: #dc3545; border: 1px solid #dc3545; border-radius: 5px;")
        exit_button.clicked.connect(self.logout)
        layout.addWidget(exit_button)

    def open_readers_module(self):
        self.readers_window = ReadersWindow()
        self.readers_window.show()
        self.modules.append(self.readers_window)

    def open_books_module(self):
        self.books_window = BooksWindow()
        self.books_window.show()
        self.modules.append(self.books_window)

    def open_registration_ticket_module(self):
        self.ticket_window = TicketWindow()
        self.ticket_window.show()
        self.modules.append(self.ticket_window)

    def logout(self):
        for module in self.modules:
            module.close()

        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()

# ======
# Окно авторизации
# ======

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация в системе управления библиотекой")
        self.setFixedSize(400, 350)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Авторизация")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Логин")
        self.login_input.setStyleSheet("padding: 8px;")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("padding: 8px;")

        self.login_button = QPushButton("Войти")
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.setStyleSheet(
            "QPushButton { background-color: #007BFF; color: white; padding: 10px; border-radius: 4px; font-weight: bold;} QPushButton:hover { background-color: #0056b3; }")
        self.login_button.clicked.connect(self.handle_login)

        layout.addWidget(self.login_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addStretch()

    @pyqtSlot()
    def handle_login(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Введите данные')
            return
        self.set_loading(True)
        asyncio.create_task(self.process_login(login, password))

    async def process_login(self, login, password):
        result = await api_service.login(login, password)
        self.set_loading(False)
        if result.get('success'):
            self.main_window = MainWindow()
            self.main_window.show()
            self.close()
        else:
            QMessageBox.critical(self, 'Ошибка', result.get('message', 'Error'))

    def set_loading(self, is_loading: bool):
        self.login_button.setEnabled(not is_loading)
        self.login_button.setText("Вход.." if is_loading else "Войти")

if __name__ == "__main__":
    application = QApplication(sys.argv)
    loop = QEventLoop(application)
    asyncio.set_event_loop(loop)

    async def init_application():
        await api_service.init_session()

    loop.run_until_complete(init_application())

    login_window = LoginWindow()
    login_window.show()

    try:
        with loop:
            loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(api_service.close_session())