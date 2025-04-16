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
            available INTEGER DEFAULT 1 -- Статус доступности номера
        )
    ''')

    # Таблица бронирований
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,      -- Связь с таблицей гостей
            room_id INTEGER NOT NULL,       -- Связь с таблицей комнат
            start_date DATE NOT NULL,       -- Дата заезда
            end_date DATE NOT NULL,         -- Дата выезда
            status TEXT DEFAULT 'active',   -- Статус бронирования: active, cancelled, completed
            FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE CASCADE,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
        )
    ''')

    # Таблица гостей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,              -- Имя гостя
            contact TEXT,                    -- Контактная информация
            preferences TEXT,                -- Личные пожелания гостя
            history TEXT                     -- История посещений (например, JSON)
        )
    ''')

    # Таблица отзывов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,       -- Связь с таблицей гостей
            review TEXT,                     -- Текст отзыва
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),  -- Оценка от 1 до 5
            admin_reply TEXT,                -- Ответ администратора
            moderated INTEGER DEFAULT 0,     -- Флаг модерации
            FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE CASCADE
        )
    ''')

    # Таблица рекомендаций для гостей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,       -- Связь с таблицей гостей
            room_id INTEGER NOT NULL,        -- Рекомендуемый номер
            reason TEXT,                     -- Причина рекомендации
            FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE CASCADE,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
        )
    ''')

    # Таблица управления персоналом
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,              -- Имя сотрудника
            role TEXT,                       -- Роль или должность
            tasks TEXT                       -- Задачи или список обязанностей
        )
    ''')

    # Таблица отчетности по задачам сотрудников
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,       -- Связь с таблицей сотрудников
            task TEXT NOT NULL,              -- Описание задачи
            status TEXT DEFAULT 'pending',   -- Статус задачи: pending, completed
            completed_at DATETIME,           -- Дата завершения задачи
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    ''')

    # Индексы для ускорения поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_id_reviews ON reviews(guest_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_room_id ON bookings(room_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_id ON bookings(guest_id)')

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

def get_recommendations(guest_id):
    """
    Генерирует рекомендации для гостя по его предпочтениям.
    Здесь в качестве примера предполагается, что в таблице guests
    может храниться предпочтительный тип номера (например, 'люкс', 'стандарт'),
    по которому и будут искаться доступные комнаты.
    """
    conn = get_db_connection()
    
    # Получаем данные гостя по его идентификатору
    guest = conn.execute('SELECT * FROM guests WHERE id = ?', (guest_id,)).fetchone()
    
    recommendations = []
    if guest:
        # Предположим, что в таблице guests есть столбец 'preferred_room_type'
        preferred_room_type = guest.get('preferred_room_type')
        if preferred_room_type:
            # Ищем все доступные комнаты выбранного типа
            rows = conn.execute('SELECT * FROM rooms WHERE type = ? AND available = 1', (preferred_room_type,)).fetchall()
            # Преобразуем результат в список словарей
            recommendations = [dict(row) for row in rows]
        else:
            # Если предпочтение не задано, можно вернуть, например, несколько наиболее доступных комнат
            rows = conn.execute('SELECT * FROM rooms WHERE available = 1 LIMIT 5').fetchall()
            recommendations = [dict(row) for row in rows]
    conn.close()
    return recommendations


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
        room_id = request.form['room_id']
        guest_id = request.form['guest_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # Проверка доступности номера
        conflict = conn.execute('''
            SELECT * FROM bookings
            WHERE room_id = ? AND status = 'active'
            AND (? < end_date AND ? > start_date)
        ''', (room_id, start_date, end_date)).fetchone()

        if conflict:
            flash("Выбранный номер занят. Попробуйте другой.", "danger")
            conn.close()
            return redirect(url_for('add_booking'))
        
        # Добавление бронирования
        conn.execute('''
            INSERT INTO bookings (guest_id, room_id, start_date, end_date, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (guest_id, room_id, start_date, end_date))
        conn.commit()
        conn.close()
        flash("Бронирование успешно создано!", "success")
        return redirect(url_for('list_bookings'))
    
    # Получение списка гостей
    guests = conn.execute('SELECT * FROM guests').fetchall()
    
    # Получение списка доступных номеров
    rooms = conn.execute('SELECT * FROM rooms WHERE available = 1').fetchall()
    
    # Генерация рекомендаций для гостя
    guest_id = request.args.get('guest_id', type=int)
    recommendations = get_recommendations(guest_id) if guest_id else []

    conn.close()
    return render_template('add_booking.html', guests=guests, rooms=rooms, recommendations=recommendations)


@app.route('/bookings/cancel/<int:booking_id>')
def cancel_booking(booking_id):
    conn = get_db_connection()
    conn.execute('UPDATE bookings SET status = "cancelled" WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()
    flash('Бронирование отменено!', 'info')
    return redirect(url_for('list_bookings'))

@app.route('/bookings/edit/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    conn = get_db_connection()
    # Получаем текущее бронирование по идентификатору
    booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    if not booking:
        flash('Бронирование не найдено', 'danger')
        conn.close()
        return redirect(url_for('list_bookings'))
    
    if request.method == 'POST':
        # Извлекаем данные из формы
        guest_id = request.form.get('guest_id')
        room_id = request.form.get('room_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # Здесь можно добавить проверку доступности номера или другие проверки,
        # например, аналогичную тому, что делается в add_booking.
        # Для простоты обновим данные напрямую:
        conn.execute('''
            UPDATE bookings 
            SET guest_id = ?, room_id = ?, start_date = ?, end_date = ?
            WHERE id = ?
        ''', (guest_id, room_id, start_date, end_date, booking_id))
        conn.commit()
        conn.close()
        flash('Бронирование успешно обновлено!', 'success')
        return redirect(url_for('list_bookings'))
    
    # Для формирования формы редактирования получим список гостей и доступных номеров.
    # При этом, чтобы позволить выбрать ранее зарезервированный номер, включим его в выборку.
    guests = conn.execute('SELECT * FROM guests').fetchall()
    rooms = conn.execute('SELECT * FROM rooms WHERE available = 1 OR id = ?', (booking['room_id'],)).fetchall()
    conn.close()
    return render_template('edit_booking.html', booking=booking, guests=guests, rooms=rooms)

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
    # Получение параметров фильтрации и сортировки из запроса
    moderated_only = request.args.get('moderated', default=None, type=int)  # Фильтрация по модерации: 0 или 1
    guest_id = request.args.get('guest_id', default=None, type=int)         # Фильтрация по гостям
    sort_by = request.args.get('sort_by', default='id', type=str)           # Сортировка: id, rating, или guest_id
    sort_order = request.args.get('sort_order', default='asc', type=str)    # Порядок сортировки: asc или desc

    conn = get_db_connection()
    query = 'SELECT * FROM reviews WHERE 1=1'  # Базовый SQL-запрос (WHERE 1=1 позволяет динамически добавлять фильтры)

    # Добавление фильтрации по модерации
    if moderated_only is not None:
        query += ' AND moderated = ?'

    # Добавление фильтрации по ID гостя
    if guest_id is not None:
        query += ' AND guest_id = ?'

    # Добавление сортировки
    query += f' ORDER BY {sort_by} {sort_order}'

    # Сбор параметров для запроса
    params = []
    if moderated_only is not None:
        params.append(moderated_only)
    if guest_id is not None:
        params.append(guest_id)

    reviews = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('reviews.html', reviews=reviews)


@app.route('/reviews/add', methods=['GET', 'POST'])
def add_review():
    if request.method == 'POST':
        guest_id = request.form['guest_id']
        review_text = request.form['review']
        rating = request.form['rating']
        
        # Проверка диапазона оценки (1-5)
        if not 1 <= int(rating) <= 5:
            flash('Оценка должна быть от 1 до 5.', 'danger')
            return redirect(url_for('add_review'))
        
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
    conn = get_db_connection()
    review = conn.execute('SELECT * FROM reviews WHERE id = ?', (review_id,)).fetchone()
    if request.method == 'POST':
        admin_reply = request.form['admin_reply']
        conn.execute('''
            UPDATE reviews
            SET admin_reply = ?, moderated = 1
            WHERE id = ?
        ''', (admin_reply, review_id))
        conn.commit()
        conn.close()
        flash('Ответ отправлен!', 'success')
        return redirect(url_for('list_reviews'))
    conn.close()
    return render_template('reply_review.html', review=review)


@app.route('/recommendations/<int:guest_id>')
def recommendations(guest_id):
    conn = get_db_connection()
    
    # Анализ истории бронирований гостя
    recent_bookings = conn.execute('''
        SELECT room_id FROM bookings
        WHERE guest_id = ?
        ORDER BY start_date DESC LIMIT 5
    ''', (guest_id,)).fetchall()
    
    # Получение типов номеров из последних бронирований
    favorite_types = []
    for booking in recent_bookings:
        room = conn.execute('SELECT type FROM rooms WHERE id = ?', (booking['room_id'],)).fetchone()
        if room and room['type'] not in favorite_types:
            favorite_types.append(room['type'])
    
    # Анализ предпочтений гостя
    guest_preferences = conn.execute('''
        SELECT preferences FROM guests
        WHERE id = ?
    ''', (guest_id,)).fetchone()
    guest_amenities = guest_preferences['preferences'] if guest_preferences else ''
    
    # Анализ отзывов гостя
    positive_reviews = conn.execute('''
        SELECT room_id FROM reviews
        WHERE guest_id = ? AND rating >= 4
    ''', (guest_id,)).fetchall()
    positive_review_rooms = [review['room_id'] for review in positive_reviews]
    
    # Составление списка рекомендуемых номеров
    query = '''
        SELECT * FROM rooms
        WHERE available = 1
        AND (
            type IN ({favorite_types}) OR
            id IN ({positive_reviews}) OR
            amenities LIKE ?
        )
    '''.format(
        favorite_types=', '.join(['?' for _ in favorite_types]),
        positive_reviews=', '.join(['?' for _ in positive_review_rooms])
    )
    
    rec_rooms = conn.execute(query, (*favorite_types, *positive_review_rooms, f"%{guest_amenities}%")).fetchall()
    
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

@app.route('/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
def edit_staff(staff_id):
    conn = get_db_connection()
    staff = conn.execute('SELECT * FROM staff WHERE id = ?', (staff_id,)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        tasks = request.form['tasks']
        conn.execute('''
            UPDATE staff
            SET name = ?, role = ?, tasks = ?
            WHERE id = ?
        ''', (name, role, tasks, staff_id))
        conn.commit()
        conn.close()
        flash('Информация о сотруднике обновлена!', 'success')
        return redirect(url_for('list_staff'))
    conn.close()
    return render_template('edit_staff.html', staff=staff)

@app.route('/staff/delete/<int:staff_id>', methods=['POST'])
def delete_staff(staff_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM staff WHERE id = ?', (staff_id,))
    conn.commit()
    conn.close()
    flash('Сотрудник успешно удалён!', 'info')
    return redirect(url_for('list_staff'))

# ======================== Задачи для персонала ========================

@app.route('/tasks', methods=['GET', 'POST'])
def manage_tasks():
    conn = get_db_connection()
    
    if request.method == 'POST':
        staff_id = request.form['staff_id']
        task = request.form['task']
        conn.execute('''
            INSERT INTO task_reports (staff_id, task, status)
            VALUES (?, ?, 'pending')
        ''', (staff_id, task))
        conn.commit()
        conn.close()
        flash('Задача назначена!', 'success')
        return redirect(url_for('manage_tasks'))
    
    # Изменённый запрос с объединением для получения имени сотрудника:
    tasks = conn.execute('''
        SELECT task_reports.id,
               staff.name AS staff_name,
               task_reports.task,
               task_reports.status,
               task_reports.completed_at
        FROM task_reports
        LEFT JOIN staff ON task_reports.staff_id = staff.id
        ORDER BY task_reports.id
    ''').fetchall()
    
    # Если нужно, можно также получить список сотрудников для формы добавления задачи:
    staff = conn.execute('SELECT * FROM staff').fetchall()
    conn.close()
    return render_template('tasks.html', tasks=tasks, staff=staff)


@app.route('/tasks/update/<int:task_id>', methods=['POST'])
def update_task(task_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE task_reports
        SET status = 'completed', completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (task_id,))
    conn.commit()
    conn.close()
    flash('Задача отмечена как выполненная!', 'success')
    return redirect(url_for('manage_tasks'))


@app.route('/tasks', methods=['GET'])
def list_tasks():
    conn = get_db_connection()
    tasks = conn.execute('''
        SELECT task_reports.id, staff.name AS staff_name, task_reports.task, task_reports.status, task_reports.completed_at
        FROM task_reports
        JOIN staff ON task_reports.staff_id = staff.id
    ''').fetchall()
    conn.close()
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/add', methods=['GET', 'POST'])
def add_task():
    conn = get_db_connection()
    if request.method == 'POST':
        staff_id = request.form['staff_id']
        task = request.form['task']
        conn.execute('''
            INSERT INTO task_reports (staff_id, task, status)
            VALUES (?, ?, 'pending')
        ''', (staff_id, task))
        conn.commit()
        conn.close()
        flash('Задача добавлена!', 'success')
        return redirect(url_for('list_tasks'))
    
    staff = conn.execute('SELECT * FROM staff').fetchall()
    conn.close()
    return render_template('add_task.html', staff=staff)

@app.route('/tasks/complete/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE task_reports
        SET status = 'completed', completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (task_id,))
    conn.commit()
    conn.close()
    flash('Задача отмечена как выполненная!', 'success')
    return redirect(url_for('list_tasks'))

# ======================== 7. Отчетность ========================

@app.route('/reports')
def reports():
    conn = get_db_connection()
    
    # Статистика по бронированиям
    stats_rows = conn.execute('''
        SELECT room_id, COUNT(*) as active_bookings
        FROM bookings
        WHERE status = 'active'
        GROUP BY room_id
    ''').fetchall()
    
    # Анализ популярности номеров (самые бронируемые номера)
    popular_rooms_rows = conn.execute('''
        SELECT room_id, COUNT(*) as total_bookings
        FROM bookings
        GROUP BY room_id
        ORDER BY total_bookings DESC
        LIMIT 5
    ''').fetchall()
    
    # Общая загрузка номеров (доступные и недоступные)
    room_load_rows = conn.execute('''
        SELECT type, 
               SUM(CASE WHEN available = 1 THEN 1 ELSE 0 END) AS available_rooms,
               SUM(CASE WHEN available = 0 THEN 1 ELSE 0 END) AS unavailable_rooms
        FROM rooms
        GROUP BY type
    ''').fetchall()
    
    conn.close()

    # Преобразуем объекты Row в словари, чтобы они были JSON-сериализуемыми
    stats = [dict(row) for row in stats_rows]
    popular_rooms = [dict(row) for row in popular_rooms_rows]
    room_load = [dict(row) for row in room_load_rows]

    return render_template('reports.html', stats=stats, popular_rooms=popular_rooms, room_load=room_load)



# ========================  Главная страница  ========================
@app.route('/')
def index():
    return render_template('index.html')

# ========================  Запуск приложения  ========================
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
