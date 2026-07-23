from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import os
import sqlite3
import json
import time
from datetime import datetime, date
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.')
app.secret_key = 'iqro_admin_super_secret_key_2026'
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = os.path.join(os.path.dirname(__file__), 'database.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "123"
}

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            price INTEGER NOT NULL,
            old_price INTEGER,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            rating REAL DEFAULT 5.0,
            tag TEXT,
            tag_type TEXT,
            image TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            UNIQUE(user_email, book_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            items_json TEXT NOT NULL,
            total_price INTEGER NOT NULL,
            status TEXT DEFAULT 'Qabul qilindi',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            comment_text TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            replies_json TEXT DEFAULT '[]',
            created_date TEXT NOT NULL
        )
    ''')

    # Migration check for existing databases
    cursor.execute("PRAGMA table_info(comments)")
    comment_cols = [row['name'] for row in cursor.fetchall()]
    if 'likes' not in comment_cols:
        cursor.execute("ALTER TABLE comments ADD COLUMN likes INTEGER DEFAULT 0")
    if 'replies_json' not in comment_cols:
        cursor.execute("ALTER TABLE comments ADD COLUMN replies_json TEXT DEFAULT '[]'")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_session_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            user_name TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            is_read INTEGER DEFAULT 0
        )
    ''')

    # Check and add is_read column if table was created previously without it
    cursor.execute("PRAGMA table_info(chat_messages)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'is_read' not in columns:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN is_read INTEGER DEFAULT 0")

    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('store_address', "Buxoro shahar, Mustaqillik ko'chasi 12"))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('maps_url', "https://maps.google.com/?q=Bukhara"))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('phone_number', "+998 90 123-45-67"))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('email_address', "info@iqro.uz"))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('admin_username', "admin"))
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('admin_password', "123"))

    cursor.execute('SELECT COUNT(*) as count FROM books')
    if cursor.fetchone()['count'] == 0:
        initial_books = [
            ("O'tkan Kunlar", "Abdulla Qodiriy", 45000, None, "badiiy", "bestseller", 4.9, "Top-1", "primary", "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&auto=format&fit=crop&q=80"),
            ("Atom Odatlari", "Djeyms Klir", 65000, 75000, "biznes", "bestseller", 5.0, "Hit", "primary", "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400&auto=format&fit=crop&q=80"),
            ("Ijtimoiy Odoblar", "Shayx Muhammad Sodiq Muhammad Yusuf", 75000, None, "diniy", "new", 5.0, "Yangi", "success", "https://images.unsplash.com/photo-1609599006353-e629aaabfeae?w=400&auto=format&fit=crop&q=80"),
            ("Boy Ota, Kambag'al Ota", "Robert Kiyosaki", 55000, 68000, "biznes", "discount", 4.7, "-20%", "danger", "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=400&auto=format&fit=crop&q=80"),
            ("Saodat Asri Qissalari (4 jildlik)", "Lutfiy Qozonchi", 220000, None, "psixologiya", "bestseller", 5.0, "Mashhur", "primary", "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400&auto=format&fit=crop&q=80"),
            ("Alkimyogar", "Paulo Koelo", 42000, None, "badiiy", "new", 4.8, "Yangi", "success", "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&auto=format&fit=crop&q=80")
        ]
        cursor.executemany('''
            INSERT INTO books (title, author, price, old_price, category, type, rating, tag, tag_type, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', initial_books)

        cursor.execute('''
            INSERT INTO comments (book_id, user_name, comment_text, created_date)
            VALUES (1, 'Sardor', 'Juda ham ajoyib asar, har bir kitobxon o''qishi shart!', '2026-07-20')
        ''')

    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin_page():
    return send_from_directory('.', 'admin.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Settings APIs
@app.route('/api/settings', methods=['GET'])
def get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM settings')
    rows = cursor.fetchall()
    settings_dict = {row['key']: row['value'] for row in rows}
    conn.close()
    return jsonify({"success": True, "settings": settings_dict})

@app.route('/api/admin/settings', methods=['POST'])
def update_settings():
    data = request.get_json() or {}
    store_address = data.get('store_address', '').strip()
    maps_url = data.get('maps_url', '').strip()
    phone_number = data.get('phone_number', '').strip()
    email_address = data.get('email_address', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    if store_address:
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('store_address', store_address))
    if maps_url:
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('maps_url', maps_url))
    if phone_number:
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('phone_number', phone_number))
    if email_address:
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('email_address', email_address))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Do'kon ma'lumotlari bazada yangilandi!"})

# Admin Auth APIs
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('admin_username',))
    u_row = cursor.fetchone()
    db_username = u_row['value'] if u_row else ADMIN_CREDENTIALS['username']

    cursor.execute('SELECT value FROM settings WHERE key = ?', ('admin_password',))
    p_row = cursor.fetchone()
    db_password = p_row['value'] if p_row else ADMIN_CREDENTIALS['password']
    conn.close()

    if username == db_username and password == db_password:
        session['admin_logged_in'] = True
        return jsonify({"success": True, "message": "Admin paneliga xush kelibsiz!"})
    else:
        return jsonify({"success": False, "message": "Login yoki parol noto'g'ri!"}), 401

@app.route('/api/admin/change-credentials', methods=['POST'])
def change_admin_credentials():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "message": "Ruxsat berilmadi!"}), 403

    data = request.get_json() or {}
    old_password = data.get('old_password', '').strip()
    new_username = data.get('new_username', '').strip()
    new_password = data.get('new_password', '').strip()

    if not new_username or not new_password or not old_password:
        return jsonify({"success": False, "message": "Barcha maydonlarni to'ldiring!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('admin_password',))
    p_row = cursor.fetchone()
    curr_password = p_row['value'] if p_row else ADMIN_CREDENTIALS['password']

    if old_password != curr_password:
        conn.close()
        return jsonify({"success": False, "message": "Eski parolingiz noto'g'ri!"}), 400

    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('admin_username', new_username))
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('admin_password', new_password))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Admin login va paroli muvaffaqiyatli o'zgartirildi!"})

@app.route('/api/admin/check-auth', methods=['GET'])
def check_admin_auth():
    if session.get('admin_logged_in'):
        return jsonify({"success": True, "logged_in": True})
    return jsonify({"success": True, "logged_in": False})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({"success": True, "message": "Chiqib ketdingiz!"})

# Admin API: Chat sessiyalar va o'qilmagan xabarlar soni
@app.route('/api/admin/chat-sessions', methods=['GET'])
def get_chat_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Barcha mavjud session_id lar tartibini olamiz (Mijoz #1, Mijoz #2 raqamlash uchun)
    cursor.execute('''
        SELECT chat_session_id, MIN(id) as first_id
        FROM chat_messages
        GROUP BY chat_session_id
        ORDER BY first_id ASC
    ''')
    session_order = [r['chat_session_id'] for r in cursor.fetchall()]
    session_index_map = {sid: idx + 1 for idx, sid in enumerate(session_order)}

    cursor.execute('''
        SELECT 
            chat_session_id, 
            user_name, 
            MAX(timestamp) as last_time, 
            (SELECT message FROM chat_messages m2 WHERE m2.chat_session_id = chat_messages.chat_session_id ORDER BY id DESC LIMIT 1) as last_message,
            SUM(CASE WHEN sender = 'user' AND is_read = 0 THEN 1 ELSE 0 END) as unread_count
        FROM chat_messages 
        GROUP BY chat_session_id 
        ORDER BY last_time DESC
    ''')
    rows = cursor.fetchall()
    sessions = []
    for r in rows:
        item = dict(r)
        # Agar user_name 'Mijoz' bo'lsa yoki 'Mijoz #' bilan boshlanmagan anonim bo'lsa
        if item['user_name'] == 'Mijoz' or not item['user_name']:
            num = session_index_map.get(item['chat_session_id'], 1)
            item['user_name'] = f"Mijoz #{num}"
        sessions.append(item)

    cursor.execute("SELECT COUNT(*) as total_unread FROM chat_messages WHERE sender = 'user' AND is_read = 0")
    total_unread = cursor.fetchone()['total_unread']

    conn.close()
    return jsonify({"success": True, "sessions": sessions, "total_unread": total_unread})

# Chat xabarlarni o'qilgan deb belgilash
@app.route('/api/chat/messages/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Admin kirganda, ushbu sessiyadagi mijoz xabarlarini 'is_read = 1' qilamiz
    cursor.execute("UPDATE chat_messages SET is_read = 1 WHERE chat_session_id = ? AND sender = 'user'", (session_id,))
    conn.commit()

    cursor.execute('SELECT * FROM chat_messages WHERE chat_session_id = ? ORDER BY id ASC', (session_id,))
    rows = cursor.fetchall()
    messages = [dict(r) for r in rows]

    # Mijoz raqamini aniqlaymiz
    cursor.execute('''
        SELECT chat_session_id, MIN(id) as first_id
        FROM chat_messages
        GROUP BY chat_session_id
        ORDER BY first_id ASC
    ''')
    session_order = [r['chat_session_id'] for r in cursor.fetchall()]
    num = session_order.index(session_id) + 1 if session_id in session_order else 1

    for msg in messages:
        if msg['user_name'] == 'Mijoz' or not msg['user_name']:
            msg['user_name'] = f"Mijoz #{num}"

    conn.close()
    return jsonify({"success": True, "messages": messages})

# SOCKET.IO REAL-TIME CHAT EVENTS
@socketio.on('join_chat')
def handle_join_chat(data):
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)

@socketio.on('join_admin')
def handle_join_admin():
    join_room('admin_room')

@socketio.on('send_message')
def handle_send_message(data):
    session_id = data.get('session_id')
    sender = data.get('sender')
    user_name = data.get('user_name', 'Mijoz')
    message_text = data.get('message', '').strip()
    current_time = datetime.now().strftime("%H:%M")

    if not session_id or not message_text:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_messages (chat_session_id, sender, user_name, message, timestamp, is_read)
        VALUES (?, ?, ?, ?, ?, 0)
    ''', (session_id, sender, user_name, message_text, current_time))
    conn.commit()

    # Sessiyalar bo'yicha Mijoz #N tartib raqamini aniqlaymiz
    cursor.execute('''
        SELECT chat_session_id, MIN(id) as first_id
        FROM chat_messages
        GROUP BY chat_session_id
        ORDER BY first_id ASC
    ''')
    session_order = [r['chat_session_id'] for r in cursor.fetchall()]
    num = session_order.index(session_id) + 1 if session_id in session_order else 1

    formatted_name = user_name
    if user_name == 'Mijoz' or not user_name:
        formatted_name = f"Mijoz #{num}"

    # Umumiy o'qilmaganlar sonini olamiz
    cursor.execute("SELECT COUNT(*) as total_unread FROM chat_messages WHERE sender = 'user' AND is_read = 0")
    total_unread = cursor.fetchone()['total_unread']
    conn.close()

    msg_payload = {
        "session_id": session_id,
        "sender": sender,
        "user_name": formatted_name,
        "message": message_text,
        "timestamp": current_time,
        "total_unread": total_unread
    }

    emit('receive_message', msg_payload, room=session_id)
    emit('receive_message', msg_payload, room='admin_room')

# Admin API: Rasm yuklash
@app.route('/api/admin/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "Rasm fayli tanlanmadi!"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "message": "Fayl tanlanmadi!"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        image_url = f"/uploads/{unique_filename}"
        return jsonify({"success": True, "message": "Rasm muvaffaqiyatli yuklandi!", "image_url": image_url})
    else:
        return jsonify({"success": False, "message": "Faqat rasm fayllari (jpg, png, webp) ruxsat etilgan!"}), 400

# Books API
@app.route('/api/books', methods=['GET'])
def get_books():
    category = request.args.get('category', 'all')
    book_type = request.args.get('type', 'all')
    search = request.args.get('search', '').lower()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM books WHERE 1=1'
    params = []

    if category != 'all':
        query += ' AND category = ?'
        params.append(category)

    if book_type != 'all':
        query += ' AND type = ?'
        params.append(book_type)

    if search:
        query += ' AND (LOWER(title) LIKE ? OR LOWER(author) LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    cursor.execute(query, params)
    books_rows = cursor.fetchall()

    books_list = []
    for row in books_rows:
        b = dict(row)
        cursor.execute('SELECT id, user_name as user, comment_text as text, likes, replies_json, created_date as date FROM comments WHERE book_id = ? ORDER BY id DESC', (b['id'],))
        raw_comments = cursor.fetchall()
        comments = []
        for c in raw_comments:
            c_dict = dict(c)
            try:
                c_dict['replies'] = json.loads(c_dict['replies_json'] or '[]')
            except Exception:
                c_dict['replies'] = []
            comments.append(c_dict)
        b['comments'] = comments
        books_list.append(b)

    conn.close()
    return jsonify({"success": True, "count": len(books_list), "books": books_list})

# Izoh qo'shish
@app.route('/api/books/<int:book_id>/comments', methods=['POST'])
def add_comment(book_id):
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    user_name = data.get('user', '').strip()

    if not user_name:
        user_name = 'Anonim'

    if not text:
        return jsonify({"success": False, "message": "Izoh matnini kiriting!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    today_str = str(date.today())
    cursor.execute('''
        INSERT INTO comments (book_id, user_name, comment_text, likes, replies_json, created_date)
        VALUES (?, ?, ?, 0, '[]', ?)
    ''', (book_id, user_name, text, today_str))
    conn.commit()

    cursor.execute('SELECT id, user_name as user, comment_text as text, likes, replies_json, created_date as date FROM comments WHERE book_id = ? ORDER BY id DESC', (book_id,))
    raw_comments = cursor.fetchall()
    updated_comments = []
    for c in raw_comments:
        c_dict = dict(c)
        try:
            c_dict['replies'] = json.loads(c_dict['replies_json'] or '[]')
        except Exception:
            c_dict['replies'] = []
        updated_comments.append(c_dict)

    conn.close()
    return jsonify({"success": True, "message": "Izohingiz muvaffaqiyatli saqlandi!", "comments": updated_comments})

# Izohga like bosish / olib tashlash API
@app.route('/api/comments/<int:comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    data = request.get_json() or {}
    action = data.get('action', 'like') # 'like' yoki 'unlike'

    conn = get_db_connection()
    cursor = conn.cursor()
    if action == 'unlike':
        cursor.execute('UPDATE comments SET likes = MAX(0, COALESCE(likes, 0) - 1) WHERE id = ?', (comment_id,))
    else:
        cursor.execute('UPDATE comments SET likes = COALESCE(likes, 0) + 1 WHERE id = ?', (comment_id,))
    conn.commit()

    cursor.execute('SELECT id, book_id, likes FROM comments WHERE id = ?', (comment_id,))
    comment = cursor.fetchone()
    conn.close()

    if comment:
        return jsonify({"success": True, "likes": comment['likes'], "book_id": comment['book_id']})
    return jsonify({"success": False, "message": "Izoh topilmadi!"}), 404

# Izohga javob (atvet) qaytarish API (Foydalanuvchi yoki Admin uchun)
@app.route('/api/comments/<int:comment_id>/reply', methods=['POST'])
def reply_comment(comment_id):
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    user_name = data.get('user', '').strip() or 'Anonim'

    if not text:
        return jsonify({"success": False, "message": "Javob matnini kiriting!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT replies_json, book_id FROM comments WHERE id = ?', (comment_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "message": "Izoh topilmadi!"}), 404

    try:
        replies = json.loads(row['replies_json'] or '[]')
    except Exception:
        replies = []

    new_reply = {
        "user": user_name,
        "text": text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    replies.append(new_reply)

    cursor.execute('UPDATE comments SET replies_json = ? WHERE id = ?', (json.dumps(replies, ensure_ascii=False), comment_id))
    conn.commit()

    book_id = row['book_id']
    cursor.execute('SELECT id, user_name as user, comment_text as text, likes, replies_json, created_date as date FROM comments WHERE book_id = ? ORDER BY id DESC', (book_id,))
    raw_comments = cursor.fetchall()
    updated_comments = []
    for c in raw_comments:
        c_dict = dict(c)
        try:
            c_dict['replies'] = json.loads(c_dict['replies_json'] or '[]')
        except Exception:
            c_dict['replies'] = []
        updated_comments.append(c_dict)

    conn.close()
    return jsonify({"success": True, "message": "Javobingiz qo'shildi!", "comments": updated_comments})

# Admin API: Kitob qo'shish
@app.route('/api/admin/books', methods=['POST'])
def add_book():
    data = request.get_json() or {}
    title = data.get('title')
    author = data.get('author')
    price = data.get('price')

    if not title or not author or not price:
        return jsonify({"success": False, "message": "Sarlavha, muallif va narx shart!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO books (title, author, price, old_price, category, type, rating, tag, tag_type, image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        title,
        author,
        int(price),
        int(data.get('old_price')) if data.get('old_price') else None,
        data.get('category', 'badiiy'),
        data.get('type', 'new'),
        float(data.get('rating', 5.0)),
        data.get('tag', 'Yangi'),
        data.get('tag_type', 'success'),
        data.get('image') or "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&auto=format&fit=crop&q=80"
    ))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({"success": True, "message": "Yangi kitob bazaga qo'shildi!", "id": new_id})

# Admin API: Kitobni tahrirlash
@app.route('/api/admin/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json() or {}
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE books SET
            title = ?,
            author = ?,
            price = ?,
            old_price = ?,
            category = ?,
            type = ?,
            image = ?
        WHERE id = ?
    ''', (
        data.get('title'),
        data.get('author'),
        int(data.get('price')),
        int(data.get('old_price')) if data.get('old_price') else None,
        data.get('category'),
        data.get('type'),
        data.get('image'),
        book_id
    ))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Kitob va narxi bazada yangilandi!"})

# Admin API: Kitobni o'chirish
@app.route('/api/admin/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    cursor.execute('DELETE FROM comments WHERE book_id = ?', (book_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Kitob bazadan o'chirildi!"})

# Admin API: Buyurtmalar
@app.route('/api/admin/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders ORDER BY order_id DESC')
    rows = cursor.fetchall()
    orders_list = []
    for r in rows:
        o = dict(r)
        o['items'] = json.loads(o['items_json'])
        orders_list.append(o)
    conn.close()
    return jsonify({"success": True, "orders": orders_list})

# Admin API: Buyurtma statusi
@app.route('/api/admin/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    data = request.get_json() or {}
    new_status = data.get('status')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', (new_status, order_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Status '{new_status}'ga o'zgartirildi!"})

# User Track API
@app.route('/api/orders/track', methods=['GET'])
def track_orders():
    phone = request.args.get('phone', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE phone LIKE ? ORDER BY order_id DESC', (f'%{phone}%',))
    rows = cursor.fetchall()
    orders_list = []
    for r in rows:
        o = dict(r)
        o['items'] = json.loads(o['items_json'])
        orders_list.append(o)
    conn.close()
    return jsonify({"success": True, "orders": orders_list})

# User Favorites API
@app.route('/api/user/favorites', methods=['POST'])
def toggle_favorite():
    data = request.get_json() or {}
    email = data.get('email')
    book_id = data.get('book_id')

    if not email:
        return jsonify({"success": False, "message": "Avval tizimga kiring!"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM favorites WHERE user_email = ? AND book_id = ?', (email, book_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('DELETE FROM favorites WHERE user_email = ? AND book_id = ?', (email, book_id))
        msg = "Kitob saralanganlardan olib tashlandi!"
    else:
        cursor.execute('INSERT INTO favorites (user_email, book_id) VALUES (?, ?)', (email, book_id))
        msg = "Kitob profil saralanganlariga saqlandi!"

    conn.commit()

    cursor.execute('SELECT book_id FROM favorites WHERE user_email = ?', (email,))
    fav_ids = [row['book_id'] for row in cursor.fetchall()]

    conn.close()
    return jsonify({"success": True, "message": msg, "favorites": fav_ids})

# User Login API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "Email va parolni kiriting!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user_row = cursor.fetchone()

    if user_row:
        if user_row['password'] == password:
            user_data = dict(user_row)
        else:
            conn.close()
            return jsonify({"success": False, "message": "Parol noto'g'ri!"}), 400
    else:
        user_name = email.split('@')[0].capitalize()
        cursor.execute('INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)', (user_name, email, password, "+998 90 000-00-00"))
        conn.commit()
        user_data = {"name": user_name, "email": email, "phone": "+998 90 000-00-00"}

    cursor.execute('SELECT book_id FROM favorites WHERE user_email = ?', (email,))
    fav_ids = [r['book_id'] for r in cursor.fetchall()]

    conn.close()
    return jsonify({
        "success": True,
        "message": "Tizimga kirdingiz!",
        "user": {
            "name": user_data["name"],
            "email": user_data["email"],
            "phone": user_data["phone"],
            "favorites": fav_ids
        }
    })

# Order Create API
@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    items = data.get('items', [])
    if not items:
        return jsonify({"success": False, "message": "Savatingiz bo'sh!"}), 400

    name = data.get('name', 'Mijoz').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    payment_method = data.get('payment_method', 'Naqd')

    if not name or not phone or not address:
        return jsonify({"success": False, "message": "Ism, telefon va manzilni kiriting!"}), 400

    total_price = sum(item['price'] * item['quantity'] for item in items)
    items_json = json.dumps(items)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO orders (customer_name, phone, address, payment_method, items_json, total_price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, phone, address, payment_method, items_json, total_price, "Qabul qilindi"))

    conn.commit()
    order_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Buyurtmangiz #{order_id} raqami bilan bazaga muvaffaqiyatli saqlandi!",
        "order_id": order_id
    })

if __name__ == '__main__':
    print("=== IQRO Real-Time Chat & Backend serveri ishga tushmoqda: http://127.0.0.1:8000 ===")
    socketio.run(app, host='0.0.0.0', port=8000, debug=True, allow_unsafe_werkzeug=True)
