from telebot import TeleBot
from config import BOT_TOKEN
from user_service import SYSTEM_PROMPT, get_or_create_user, continue_dialog, start_new_dialog
from handlers import register_handlers
from database_manager import DatabaseManager
from flask import Flask, request, jsonify, send_from_directory
import threading
import os
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
APP_DIR = os.path.join(PROJECT_ROOT, 'app')

db = DatabaseManager()
db.init_db()

bot = TeleBot(str(BOT_TOKEN))
register_handlers(bot)

app = Flask(__name__)

@app.route('/api/session/<int:session_id>')
def get_session():
    return jsonify({"error": "This function is unable"}), 404

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        telegram_id = data.get('telegram_id')

        if not user_message:
            return jsonify({"error": "Пустое сообщение"}), 400

        from gigachat_client import get_ai_response

        if telegram_id:
            user = get_or_create_user(telegram_id)
            if not session_id:
                session, _, _ = continue_dialog(telegram_id)
                if not session:
                    session_id, _ = start_new_dialog(telegram_id)
                else:
                    session_id = session['id']

        if not session_id:
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sessions (status, messages, telegram_id)
                    VALUES (?, ?, ?)
                ''', ('active', json.dumps([{"role": "system", "content": SYSTEM_PROMPT}]), telegram_id))
                session_id = cursor.lastrowid
                conn.commit()
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT messages FROM sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "Сессия не найдена"}), 400

            messages = json.loads(row['messages'])

        messages.append({"role": "user", "content": user_message})

        try:
            ai_response = get_ai_response(messages)
        except Exception as e:
            ai_response = f"Ошибка ИИ: {e}"

        messages.append({"role": "assistant", "content": ai_response})

        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions SET messages = ? WHERE id = ?
            ''', (json.dumps(messages, ensure_ascii=False), session_id))
            conn.commit()

        return jsonify({
            "response": ai_response,
            "session_id": session_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return send_from_directory(APP_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    file_path = os.path.join(APP_DIR, filename)
    if os.path.exists(file_path):
        return send_from_directory(APP_DIR, filename)
    return "Файл не найден", 404

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    print("🚀 Запуск Flask API...")
    threading.Thread(target=run_flask, daemon=True).start()

    print("🤖 Запуск Telegram бота...")
    bot.infinity_polling(none_stop=True)