import random
import string
from database_manager import DatabaseManager, sqlite3

db = DatabaseManager()

def generate_login():
    """Генерация логина вида TW-XXXXXX"""
    return "TW-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_password():
    """Генерация пароля из 8 символов (буквы + цифры)"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def create_user(telegram_id, email=None, role='student', paid=False):
    """Создать пользователя с автоматической генерацией логина/пароля"""
    login = generate_login()
    password = generate_password()
    with db.connect() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (telegram_id, login, password, email, role, paid)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (telegram_id, login, password, email, role, paid))
            conn.commit()
            return cursor.lastrowid, login, password
        except sqlite3.IntegrityError:
            return None, None, None

def get_user_by_telegram_id(telegram_id):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone()

def get_user_by_login(login):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE login = ?', (login,))
        return cursor.fetchone()

def set_user_paid(telegram_id):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET paid = 1, paid_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', (telegram_id,))
        conn.commit()

def create_session(user_id):
    user = get_user_by_telegram_id(user_id)
    telegram_id = user['telegram_id'] if user else None
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (user_id, status, messages, telegram_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'active', '[]', telegram_id))
        conn.commit()
        return cursor.lastrowid



def get_active_session(user_id):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sessions WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        return cursor.fetchone()

def get_session_by_id(session_id):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        return cursor.fetchone()

def update_session_messages(session_id, messages_json):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sessions SET messages = ? WHERE id = ?
        ''', (messages_json, session_id))
        conn.commit()

def update_session_status(session_id, status):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sessions SET status = ? WHERE id = ?
        ''', (status, session_id))
        conn.commit()

def update_session_result(session_id, tracks_json, review_text):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sessions SET result_tracks = ?, result_review = ?, status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (tracks_json, review_text, session_id))
        conn.commit()

def generate_parent_code(session_id):
    code = ''.join(random.choices(string.digits, k=6))
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET parent_code = ? WHERE id = ?', (code, session_id))
        conn.commit()
    return code

def get_session_by_parent_code(code):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sessions WHERE parent_code = ?', (code,))
        return cursor.fetchone()

def get_all_users():
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        return cursor.fetchall()

def get_statistics():
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE paid = 1')
        paid_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT AVG(LENGTH(messages)) FROM sessions WHERE status = "completed"')
        avg_dialog_len = cursor.fetchone()[0] or 0
        return total_users, paid_count, avg_dialog_len