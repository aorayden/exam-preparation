import json
import os
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

FILES_DIR = os.path.dirname(os.path.abspath(__file__))

BOOKS_FILE = os.path.join(FILES_DIR, 'books.json')
USERS_FILE = os.path.join(FILES_DIR, 'readers.json')
TICKETS_FILE = os.path.join(FILES_DIR, 'tickets.json')

# ======
# Сущности
# ======

class Book(BaseModel):
    code: str
    author: str
    name: str
    year_publication: int
    sign_novelty_and_annotations: str

class User(BaseModel):
    card_number: int
    surname: str
    name: str
    patronymic: str
    address: str
    phone: str
    login: Optional[str] = None
    password: Optional[str] = None
    role: str

class ReaderTicket(BaseModel):
    reader_card_number: int
    books: List[str] = []
    date_issue: str
    date_return: str

# ======
# Вспомогательные функции
# ======

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding="utf-8") as file:
            return json.load(file)
    except:
        return []

def save_json(filepath, data):
    with open(filepath, 'w', encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def get_next_card_id(users):
    if not users:
        return 1
    return max(user['card_number'] for user in users) + 1

# ======
# Стандартное заполнение
# ======

def create_default_books():
    if not os.path.exists(BOOKS_FILE):
        default_books = [
            {
                'code': 'ISPB-0001',
                'author': 'Каримова О.В.',
                'name': 'ПМ.01',
                'year_publication': 2025,
                'sign_novelty_and_annotations': 'Здесь ничего нет.',
            },
            {
                'code': 'ISPB-0002',
                'author': 'Набиева Л.Р.',
                'name': 'РМП',
                'year_publication': 2025,
                'sign_novelty_and_annotations': 'Здесь ничего нет.',
            },
            {
                'code': 'ISPB-0003',
                'author': 'Кузовкина В.Д.',
                'name': 'МДК.01.04.',
                'year_publication': 2025,
                'sign_novelty_and_annotations': 'Здесь ничего нет.',
            },
        ]

        save_json(BOOKS_FILE, default_books)
        print('Стандартные книги добавлены.')

def create_default_users():
    if not os.path.exists(USERS_FILE):
        default_users = [
            {
                'card_number': 1,
                'surname': 'Кузовкина',
                'name': 'Виктория',
                'patronymic': 'Денисовна',
                'address': 'ул. Кирова 61/2',
                'phone': '+79172371470',
                'login': None,
                'password': None,
                'role': 'Читатель',
            },
            {
                'card_number': 2,
                'surname': 'Файзельгаянов',
                'name': 'Ильнур',
                'patronymic': 'Фадисович',
                'address': 'ул. Кирова 122/3',
                'phone': '+79272371470',
                'login': 'aorayden',
                'password': '*<i51V7CEkgS',
                'role': 'Администратор',
            },
        ]

        save_json(USERS_FILE, default_users)
        print('Стандартные пользователи добавлены.')

def create_default_tickets():
    if not os.path.exists(TICKETS_FILE):
        default_tickets = [
            {
                'reader_card_number': 1,
                'books': [
                    'ISPB-0002',
                    'ISPB-0003',
                ],
                'date_issue': '24.12.2025',
                'date_return': '26.12.2025',
            },
        ]

        save_json(TICKETS_FILE, default_tickets)
        print('Стандартные читательские билеты добавлены.')

# ======
# Точки выхода
# ======

# ===
# Запросы и модели
# ===

class LoginRequest(BaseModel):
    login: Optional[str] = None
    password: Optional[str] = None
    card_number: Optional[int] = None

class UserRegister(BaseModel):
    surname: str
    name: str
    patronymic: str
    address: str
    phone: str
    login: Optional[str] = None
    password: Optional[str] = None
    role: str = 'Читатель'

# ===

class Response(BaseModel):
    success: bool
    message: str
    user: Optional[User] = None

# Авторизация.
@app.post('/auth/login', response_model=Response)
def login_user(credentials: LoginRequest):
    users_data = load_json(USERS_FILE)

    found_user = None

    if credentials.login and credentials.password:
        for u in users_data:
            if u.get('login') == credentials.login and u.get('password') == credentials.password:
                found_user = u
                break

    elif credentials.card_number:
        for u in users_data:
            if u.get('card_number') == credentials.card_number:
                found_user = u
                break

    if not found_user:
        return Response(success=False, message="Неверные учётные данные или пользователь не найден.")

    return Response(
        success=True,
        message=f"Добро пожаловать, {found_user['name']} {found_user['patronymic']}!",
        user=User(**found_user)
    )

# Регистрация.
@app.post('/auth/register', response_model=Response)
def register_user(new_user_data: UserRegister):
    users_data = load_json(USERS_FILE)

    for u in users_data:
        if u.get('phone') == new_user_data.phone:
            return Response(success=False, message="Пользователь с таким номером телефона уже существует")

    new_id = get_next_card_id(users_data)

    user_dict = new_user_data.dict()
    user_dict['card_number'] = new_id

    users_data.append(user_dict)
    save_json(USERS_FILE, users_data)

    created_user = User(**user_dict)

    return Response(
        success=True,
        message=f"Пользователь успешно зарегистрирован. Номер читательского билета: {new_id}",
        user=created_user
    )

# Все читатели.
@app.get('/readers', response_model=List[User])
def get_all_readers():
    users_data = load_json(USERS_FILE)
    return [User(**u) for u in users_data if u.get('role') == 'Читатель']

# Все книги.
@app.get('/books', response_model=List[Book])
def get_all_books():
    books_data = load_json(BOOKS_FILE)
    return [Book(**b) for b in books_data]

# Добавление книги.
@app.post('/books/add', response_model=Response)
def add_book(new_book_data: Book):
    books_data = load_json(BOOKS_FILE)

    for b in books_data:
        if b.get('code') == new_book_data.code:
            return Response(success=False, message=f'Книга с кодом {new_book_data.code} уже существует.')

    books_data.append(new_book_data.dict())
    save_json(BOOKS_FILE, books_data)

    return Response(success=True, message='Книга успешно добавлена в систему.')

# Все книги доступные для оформления.
@app.get('/books/available', response_model=List[Book])
def get_available_books():
    books_data = load_json(BOOKS_FILE)
    tickets_data = load_json(TICKETS_FILE)

    busy_codes = set()
    for t in tickets_data:
        for code in t.get('books', []):
            busy_codes.add(code)

    available = [Book(**b) for b in books_data if b['code'] not in busy_codes]
    return available

# Создать чит. дневник.
@app.post('/tickets/create', response_model=Response)
def create_ticket(ticket: ReaderTicket):
    tickets_data = load_json(TICKETS_FILE)
    books_data = load_json(BOOKS_FILE)
    users_data = load_json(USERS_FILE)

    reader_exists = False
    for user in users_data:
        if user.get('card_number') == ticket.reader_card_number:
            reader_exists = True
            break

    if not reader_exists:
        return Response(success=False, message="Пользователь с таким номером читательского билета не найден")

    all_book_codes = {b['code'] for b in books_data}
    for code in ticket.books:
        if code not in all_book_codes:
            return Response(success=False, message=f"Книга с кодом {code} не существует в библиотеке")

    busy_codes = set()
    for t in tickets_data:
        for code in t.get('books', []):
            busy_codes.add(code)

    for code in ticket.books:
        if code in busy_codes:
            return Response(success=False, message=f"Книга с кодом {code} уже выдана другому читателю")

    tickets_data.append(ticket.dict())
    save_json(TICKETS_FILE, tickets_data)

    return Response(success=True, message="Читательский билет успешно оформлен")

# Вернуть список книг по чит. дневнику.
@app.get('/tickets/{card_number}/books', response_model=List[Book])
def get_reader_issued_books(card_number: int):
    tickets_data = load_json(TICKETS_FILE)
    books_data = load_json(BOOKS_FILE)

    reader_book_codes = set()
    for t in tickets_data:
        if t.get('reader_card_number') == card_number:
            for code in t.get('books', []):
                reader_book_codes.add(code)

    reader_books = [Book(**b) for b in books_data if b['code'] in reader_book_codes]

    return reader_books

# ======
# Запуск сервера
# Команда: uvicorn server:app --reload --port 5079
# ======

@app.on_event('startup')
async def startup():
    print('Запуск сервера..\nПроверка данных системы..\n')
    create_default_books()
    create_default_users()
    create_default_tickets()