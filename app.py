import os
import sqlite3

from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, flash


app = Flask(__name__)

app.url_map.strict_slashes = False

app.jinja_env.globals['datetime'] = datetime

app.secret_key = 'secret_key_for_session'
DATABASE = 'hotel.db'

# Функция для получения соединения с базой данных
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # позволит обращаться по именам столбцов
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица для управления номерами
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,         -- Категория номера (например, "Стандарт", "Люкс")
            capacity INTEGER,           -- Вместимость номера
            amenities TEXT,             -- Удобства номера (Wi-Fi, кондиционер и т.д.)
            price REAL,                 -- Цена за номер
            photo TEXT,                 -- Путь к файлу фотографии номера (например, uploads/room1.jpg)
            available INTEGER DEFAULT 1 -- Значение 1 означает, что номер доступен, 0 – недоступен
        )
    ''')

        # Добавление индекса для ускорения поиска по комнатам
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_room_id ON bookings(room_id)')
    
    # Таблица бронирований
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,      -- Связь с таблицей гостей
            room_id INTEGER NOT NULL,       -- Связь с таблицей комнат
            start_date DATE NOT NULL,       -- Дата заезда (смена типа на DATE)
            end_date DATE NOT NULL,         -- Дата выезда (смена типа на DATE)
            status TEXT DEFAULT 'active',   -- Статус бронирования: active, cancelled, completed
            FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE CASCADE, -- Укрепление связи с таблицей гостей
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL   -- Укрепление связи с таблицей комнат
        )
    ''')

        # Таблица учета гостей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,              -- Имя гостя (обязательно)
            contact TEXT,                    -- Контактная информация
            preferences TEXT,                -- Личные пожелания гостя
            history TEXT                     -- История посещений (например, JSON)
        )
    ''')

        # Таблица истории гостей (опционально, нормализация данных истории)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guest_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,       -- Связь с таблицей гостей
            booking_id INTEGER NOT NULL,     -- Связь с таблицей бронирований
            FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE CASCADE,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        )
    ''')

        # Добавление индекса для ускорения поиска по гостям
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_id ON bookings(guest_id)')

    # Таблица отзывов (связь с гостями)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER,
            review TEXT,
            rating INTEGER,
            admin_reply TEXT,
            moderated INTEGER DEFAULT 0,
            FOREIGN KEY (guest_id) REFERENCES guests(id)
        )
    ''')
    
    # Таблица отзывов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER,
            review TEXT,               -- Текст отзыва
            rating INTEGER,            -- Оценка гостя (например, от 1 до 5)
            admin_reply TEXT,          -- Ответ администратора
            moderated INTEGER DEFAULT 0,  -- Флаг модерации (0 - не модераторован, 1 - модераторован)
            FOREIGN KEY (guest_id) REFERENCES guests(id)
        )
    ''')
    
    # Таблица управления персоналом
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,        -- Имя сотрудника
            role TEXT,                 -- Роль или должность (например, администратор, горничная)
            tasks TEXT                 -- Задачи или список обязанностей
        )
    ''')
    
    conn.commit()
    conn.close()

# ======================== 1. Управление номерами ========================

@app.route('/rooms', methods=["GET"])
def list_rooms():
    conn = get_db_connection()
    query = "SELECT * FROM rooms WHERE 1=1"
    params = []

    # Фильтр по типу (категории)
    room_type = request.args.get('type')
    if room_type and room_type.lower() != "all":
        query += " AND type = ?"
        params.append(room_type)

    # Фильтр по доступности: если передано значение "1" или "0"
    available = request.args.get('available')
    if available in ['0', '1']:
        query += " AND available = ?"
        params.append(available)

    rooms = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('rooms.html', rooms=rooms)


@app.route('/rooms/add', methods=['GET', 'POST'])
def add_room():
    if request.method == 'POST':
        room_type = request.form['type']
        capacity = request.form.get('capacity', 0)
        amenities = request.form.get('amenities', '')
        price = request.form.get('price', 0.0)
        # Для доступности можно использовать чекбокс или select; преобразуем в целое:
        available = 1 if request.form.get('available') == 'on' else 0
        
        photo = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                photo_dir = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(photo_dir, exist_ok=True)
                # Здесь можно добавить логику генерации уникального имени файла, например, с помощью uuid
                photo_path = os.path.join('uploads', file.filename)
                file.save(os.path.join(app.root_path, 'static', photo_path))
                photo = photo_path
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO rooms (type, capacity, amenities, price, photo, available)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (room_type, capacity, amenities, price, photo, available))
        conn.commit()
        conn.close()
        flash('Комната успешно добавлена!', 'success')
        return redirect(url_for('list_rooms'))
    return render_template('add_room.html')


@app.route('/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
def edit_room(room_id):
    conn = get_db_connection()
    room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room is None:
        flash("Комната не найдена", "danger")
        return redirect(url_for('list_rooms'))
    
    if request.method == 'POST':
        room_type = request.form['type']
        capacity = request.form.get('capacity', 0)
        amenities = request.form.get('amenities', '')
        price = request.form.get('price', 0.0)
        # Обработка флажка доступности
        available = 1 if request.form.get('available') == 'on' else 0
        
        # Сохраняем текущее фото, если новое не загружено
        photo = room['photo']
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                # Опционально: можно генерировать уникальное имя файла, например, используя uuid
                photo_dir = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(photo_dir, exist_ok=True)
                photo_path = os.path.join('uploads', file.filename)
                file.save(os.path.join(app.root_path, 'static', photo_path))
                photo = photo_path
        
        conn.execute('''
            UPDATE rooms
            SET type = ?, capacity = ?, amenities = ?, price = ?, photo = ?, available = ?
            WHERE id = ?
        ''', (room_type, capacity, amenities, price, photo, available, room_id))
        conn.commit()
        conn.close()
        flash('Данные комнаты обновлены!', 'success')
        return redirect(url_for('list_rooms'))
    
    conn.close()
    return render_template('edit_room.html', room=room)

@app.route('/rooms/delete/<int:room_id>', methods=['POST'])
def delete_room(room_id):
    conn = get_db_connection()
    # Удаляем комнату из базы данных
    conn.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
    conn.commit()
    conn.close()
    flash('Комната успешно удалена!', 'success')
    return redirect(url_for('list_rooms'))

# ======================== 2. Бронирование ========================

# Функция проверки доступности номера на указанный период
def check_availability(room_id, start_date, end_date):
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT * FROM bookings
        WHERE room_id = ? AND status = 'active'
        AND NOT (
            date(end_date) < date(?) OR date(start_date) > date(?)
        )
    ''', (room_id, start_date, end_date)).fetchall()
    conn.close()
    return len(bookings) == 0

@app.route('/bookings')
def list_bookings():
    conn = get_db_connection()
    bookings = conn.execute('SELECT * FROM bookings').fetchall()
    conn.close()
    return render_template('bookings.html', bookings=bookings)

@app.route('/bookings/add', methods=['GET', 'POST'])
def add_booking():
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Получаем данные из формы
        room_id = request.form['room_id']
        guest_id = request.form.get('guest_id')  # предполагается, что ID гостя передаётся корректно
        start_date = request.form['start_date']   # формат: YYYY-MM-DD
        end_date = request.form['end_date']       # формат: YYYY-MM-DD

        # Проверка пересечения дат бронирования для выбранной комнаты
        conflict = conn.execute('''
            SELECT * FROM bookings
            WHERE room_id = ?
              AND status = 'active'
              AND (? < end_date AND ? > start_date)
        ''', (room_id, start_date, end_date)).fetchone()

        if conflict:
            flash("На выбранные даты номер уже забронирован. Пожалуйста, выберите другие даты.", "danger")
            conn.close()
            return redirect(url_for('add_booking'))
        
        # Если пересечений нет, создаём бронирование
        conn.execute('''
            INSERT INTO bookings (guest_id, room_id, start_date, end_date, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (guest_id, room_id, start_date, end_date))
        conn.commit()
        conn.close()
        flash('Бронирование успешно создано!', 'success')
        return redirect(url_for('list_bookings'))
    
    # GET-запрос: выбираем список доступных комнат
    rooms = conn.execute("SELECT * FROM rooms WHERE available = 1").fetchall()
    conn.close()
    return render_template('add_booking.html', rooms=rooms)



@app.route('/bookings/cancel/<int:booking_id>')
def cancel_booking(booking_id):
    conn = get_db_connection()
    conn.execute('UPDATE bookings SET status = "cancelled" WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()
    flash('Бронирование отменено!', 'info')
    return redirect(url_for('list_bookings'))

# ======================== 3. Учет гостей ========================

@app.route('/guests')
def list_guests():
    conn = get_db_connection()
    guests = conn.execute('SELECT * FROM guests').fetchall()
    conn.close()
    return render_template('guests.html', guests=guests)

@app.route('/guests/register', methods=['GET', 'POST'])
def register_guest():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        preferences = request.form['preferences']
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO guests (name, contact, preferences)
            VALUES (?, ?, ?)
        ''', (name, contact, preferences))
        conn.commit()
        conn.close()
        flash('Гость зарегистрирован!', 'success')
        return redirect(url_for('list_guests'))
    return render_template('register_guest.html')

@app.route('/guests/<int:guest_id>/history')
def guest_history(guest_id):
    conn = get_db_connection()
    history = conn.execute('''
        SELECT bookings.start_date, bookings.end_date, bookings.status, rooms.type, rooms.price
        FROM bookings
        JOIN rooms ON bookings.room_id = rooms.id
        WHERE bookings.guest_id = ?
    ''', (guest_id,)).fetchall()
    conn.close()
    return render_template('guest_history.html', history=history, guest_id=guest_id)

@app.route('/guests/<int:guest_id>', methods=['GET'])
def guest_profile(guest_id):
    conn = get_db_connection()
    guest = conn.execute('SELECT * FROM guests WHERE id = ?', (guest_id,)).fetchone()
    if guest is None:
        flash("Гость не найден.", "danger")
        conn.close()
        return redirect(url_for('list_guests'))

    bookings = conn.execute('''
        SELECT rooms.type, bookings.start_date, bookings.end_date, bookings.status
        FROM bookings
        JOIN rooms ON bookings.room_id = rooms.id
        WHERE bookings.guest_id = ?
    ''', (guest_id,)).fetchall()
    
    reviews = conn.execute('''
        SELECT reviews.review, reviews.rating, reviews.admin_reply
        FROM reviews
        WHERE reviews.guest_id = ?
    ''', (guest_id,)).fetchall()
    
    conn.close()
    return render_template('guest_profile.html', guest=guest, bookings=bookings, reviews=reviews)


# ======================== 4. Отзывы ========================

@app.route('/reviews')
def list_reviews():
    conn = get_db_connection()
    reviews = conn.execute('SELECT * FROM reviews').fetchall()
    conn.close()
    return render_template('reviews.html', reviews=reviews)

@app.route('/reviews/add', methods=['GET', 'POST'])
def add_review():
    if request.method == 'POST':
        guest_id = request.form['guest_id']
        review_text = request.form['review']
        rating = request.form['rating']
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO reviews (guest_id, review, rating)
            VALUES (?, ?, ?)
        ''', (guest_id, review_text, rating))
        conn.commit()
        conn.close()
        flash('Отзыв добавлен!', 'success')
        return redirect(url_for('list_reviews'))
    conn = get_db_connection()
    guests = conn.execute('SELECT * FROM guests').fetchall()
    conn.close()
    return render_template('add_review.html', guests=guests)

@app.route('/reviews/reply/<int:review_id>', methods=['GET', 'POST'])
def reply_review(review_id):
    if request.method == 'POST':
        admin_reply = request.form['admin_reply']
        conn = get_db_connection()
        conn.execute('''
            UPDATE reviews
            SET admin_reply = ?, moderated = 1
            WHERE id = ?
        ''', (admin_reply, review_id))
        conn.commit()
        conn.close()
        flash('Ответ отправлен!', 'success')
        return redirect(url_for('list_reviews'))
    conn = get_db_connection()
    review = conn.execute('SELECT * FROM reviews WHERE id = ?', (review_id,)).fetchone()
    conn.close()
    return render_template('reply_review.html', review=review)

# ======================== 5. Персонализированные рекомендации ========================

@app.route('/recommendations/<int:guest_id>')
def recommendations(guest_id):
    conn = get_db_connection()
    # Простейшая логика: берем последнее бронирование гостя и рекомендуем номера такого же типа
    booking = conn.execute('''
        SELECT room_id FROM bookings
        WHERE guest_id = ?
        ORDER BY id DESC LIMIT 1
    ''', (guest_id,)).fetchone()
    rec_rooms = []
    if booking:
        room = conn.execute('SELECT type FROM rooms WHERE id = ?', (booking['room_id'],)).fetchone()
        if room:
            rec_rooms = conn.execute('''
                SELECT * FROM rooms WHERE type = ? AND available = 1
            ''', (room['type'],)).fetchall()
    conn.close()
    return render_template('recommendations.html', rec_rooms=rec_rooms)

# ======================== 6. Управление персоналом ========================

@app.route('/staff')
def list_staff():
    conn = get_db_connection()
    staff = conn.execute('SELECT * FROM staff').fetchall()
    conn.close()
    return render_template('staff.html', staff=staff)

@app.route('/staff/add', methods=['GET', 'POST'])
def add_staff():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        tasks = request.form['tasks']
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO staff (name, role, tasks)
            VALUES (?, ?, ?)
        ''', (name, role, tasks))
        conn.commit()
        conn.close()
        flash('Сотрудник добавлен!', 'success')
        return redirect(url_for('list_staff'))
    return render_template('add_staff.html')

# ======================== 7. Отчетность ========================

@app.route('/reports')
def reports():
    conn = get_db_connection()
    # Пример отчёта: количество активных бронирований по каждому номеру
    stats = conn.execute('''
        SELECT room_id, COUNT(*) as count
        FROM bookings
        WHERE status = 'active'
        GROUP BY room_id
    ''').fetchall()
    conn.close()
    return render_template('reports.html', stats=stats)

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Запуск приложения
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
