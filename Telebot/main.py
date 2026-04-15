from telebot import TeleBot
from config import BOT_TOKEN
from user_service import SYSTEM_PROMPT, extract_review_from_ai_response, extract_tracks_from_ai_response
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

        if not session_id:
            with db.connect() as conn:
                cursor = conn.cursor()
                conn.execute("""
                UPDATE sessions SET status = 'aborted'
                WHERE telegram_id = ? AND status = 'active'
                """, (telegram_id,))
                conn.commit()

                if not telegram_id:
                    return jsonify({"error": "Требуется telegram_id для новой сессии"}), 400

                cursor.execute('''
                    INSERT INTO sessions (status, messages, telegram_id)
                    VALUES (?, ?, ?)
                ''', ('active', json.dumps([{"role": "system", "content": SYSTEM_PROMPT}], ensure_ascii=False), telegram_id))
                session_id = cursor.lastrowid
                conn.commit()

        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT messages, status, telegram_id FROM sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "Сессия не найдена"}), 400

            if row['status'] == 'completed':
                return jsonify({"response": "Диалог завершён. Начните новый.", "session_id": session_id})

            messages = json.loads(row['messages'])

        messages.append({"role": "user", "content": user_message})
        ai_response = get_ai_response(messages)
        messages.append({"role": "assistant", "content": ai_response})

        if "✅ Вот твои карьерные треки!" in ai_response:
            tracks = extract_tracks_from_ai_response(ai_response)
            review = extract_review_from_ai_response(ai_response)

            with db.connect() as conn:
                conn.execute('''
                    UPDATE sessions 
                    SET messages = ?, result_tracks = ?, result_review = ?, status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    json.dumps(messages, ensure_ascii=False),
                    json.dumps(tracks, ensure_ascii=False),
                    review,
                    session_id
                ))
                conn.commit()
        else:
            with db.connect() as conn:
                conn.execute('UPDATE sessions SET messages = ? WHERE id = ?', (
                    json.dumps(messages, ensure_ascii=False),
                    session_id
                ))
                conn.commit()

        return jsonify({
            "response": ai_response,
            "session_id": session_id
        })

    except Exception as e:
        if "401" in str(e) or "Unauthorized" in str(e) or "токен" in str(e).lower():
            return jsonify({
            "error": "Сессия истекла. Требуется обновление доступа к ИИ.",
            "session_expired": True
        }), 500
        else:
            return jsonify({"error": "Ошибка сервера. Попробуйте позже."}), 500

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