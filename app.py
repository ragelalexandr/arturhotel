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

# Инициализация базы данных: создаём таблицы для всех модулей
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица для управления номерами
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            capacity INTEGER,
            amenities TEXT,
            price REAL,
            photo TEXT,           -- путь к файлу фотографии
            available INTEGER DEFAULT 1
        )
    ''')
    
    # Таблица бронирований
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER,
            room_id INTEGER,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'active',  -- active, cancelled, completed
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    ''')
    
    # Таблица учета гостей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            preferences TEXT
        )
    ''')
    
    # Таблица отзывов
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
    
    # Таблица управления персоналом
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            tasks TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# ======================== 1. Управление номерами ========================

@app.route('/rooms')
def list_rooms():
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms').fetchall()
    conn.close()
    return render_template('rooms.html', rooms=rooms)

@app.route('/rooms/add', methods=['GET', 'POST'])
def add_room():
    if request.method == 'POST':
        room_type = request.form['type']
        capacity = request.form['capacity']
        amenities = request.form['amenities']
        price = request.form['price']
        photo = None
        # Если загружается фотография
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                photo_dir = os.path.join('static', 'uploads')
                os.makedirs(photo_dir, exist_ok=True)
                photo_path = os.path.join(photo_dir, file.filename)
                file.save(photo_path)
                photo = photo_path
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO rooms (type, capacity, amenities, price, photo)
            VALUES (?, ?, ?, ?, ?)
        ''', (room_type, capacity, amenities, price, photo))
        conn.commit()
        conn.close()
        flash('Комната добавлена!', 'success')
        return redirect(url_for('list_rooms'))
    return render_template('add_room.html')

@app.route('/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
def edit_room(room_id):
    conn = get_db_connection()
    room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
    if request.method == 'POST':
        room_type = request.form['type']
        capacity = request.form['capacity']
        amenities = request.form['amenities']
        price = request.form['price']
        conn.execute('''
            UPDATE rooms
            SET type = ?, capacity = ?, amenities = ?, price = ?
            WHERE id = ?
        ''', (room_type, capacity, amenities, price, room_id))
        conn.commit()
        conn.close()
        flash('Комната обновлена!', 'success')
        return redirect(url_for('list_rooms'))
    conn.close()
    return render_template('edit_room.html', room=room)

@app.route('/rooms/delete/<int:room_id>')
def delete_room(room_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
    conn.commit()
    conn.close()
    flash('Комната удалена!', 'info')
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
    # Выбираем доступные комнаты для бронирования
    rooms = conn.execute('SELECT * FROM rooms WHERE available = 1').fetchall()
    guests = conn.execute('SELECT * FROM guests').fetchall()
    conn.close()
    if request.method == 'POST':
        guest_id = request.form['guest_id']
        room_id = request.form['room_id']
        start_date = request.form['start_date']  # формат YYYY-MM-DD
        end_date = request.form['end_date']
        
        if not check_availability(room_id, start_date, end_date):
            flash('Комната недоступна на выбранные даты!', 'danger')
            return redirect(url_for('add_booking'))
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO bookings (guest_id, room_id, start_date, end_date)
            VALUES (?, ?, ?, ?)
        ''', (guest_id, room_id, start_date, end_date))
        conn.commit()
        conn.close()
        flash('Бронирование создано!', 'success')
        return redirect(url_for('list_bookings'))
        
    return render_template('add_booking.html', rooms=rooms, guests=guests)

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
    history = conn.execute('SELECT * FROM bookings WHERE guest_id = ?', (guest_id,)).fetchall()
    conn.close()
    return render_template('guest_history.html', history=history)

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
