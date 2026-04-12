import json
import re
from user_repository import *
from gigachat_client import get_ai_response

SYSTEM_PROMPT = """Ты — профессиональный психолог-профориентолог. Веди дружескую беседу со школьником. Задавай вопросы по одному. 
Узнай: имя, класс, город, профиль школы, интересы, хобби, любимые предметы, сильные стороны, участие в олимпиадах/проектах, 
ценности в работе (доход, творчество, помощь людям, график, карьерный рост). Пиши, желательно, 2-3 предложениями. По завершении составь 2–3 карьерных трека и обязательно напиши слова "трек" или "треки" в своем ответе. 
Каждый трек: название профессии, подробное описание (реальная суть работы), зарплата в городе ученика, ВУЗы для поступления,
средние проходные баллы по предметам (постарайся узнать точные данные о баллах), курсы/кружки для старта прямо сейчас. Также составь отзыв о скрытых способностях ученика."""

def get_or_create_user(telegram_id):
    """Возвращает user_id и данные пользователя, при необходимости создаёт запись"""
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        user_id, login, password = create_user(telegram_id)
        user = get_user_by_telegram_id(telegram_id)
    return user

def check_paid(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    return user and user['paid'] == 1

def simulate_payment(telegram_id):
    """Искусственная оплата"""
    set_user_paid(telegram_id)
    user = get_user_by_telegram_id(telegram_id)
    return user['login'], user['password']

def start_new_dialog(telegram_id):
    """Начинает новую активную сессию для пользователя"""
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return None, "Пожалуйста, сначала зарегистрируйтесь (просто напишите /start)."
    
    with db.connect() as conn:
        conn.execute("UPDATE sessions SET status = 'aborted' WHERE user_id = ? AND status = 'active'", (user['id'],))
        conn.commit()

    session_id = create_session(user['id'])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    update_session_messages(session_id, json.dumps(messages, ensure_ascii=False))
    return session_id, None

def continue_dialog(telegram_id):
    """Возвращает активную сессию и сообщения"""
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return None, None, "Пожалуйста, зарегистрируйтесь."
    session = get_active_session(user['id'])
    if not session:
        return None, None, "У вас нет активного диалога. Начните новый с помощью /start."
    messages = json.loads(session['messages'])
    return session, messages, None

def add_user_message(session_id, user_message):
    """Добавляет сообщение пользователя в сессию, возвращает обновлённые сообщения и ответ ИИ"""
    session = get_session_by_id(session_id)
    if not session:
        return [], "Сессия не найдена", None, None, None

    try:
        messages = json.loads(session['messages'])
    except (json.JSONDecodeError, TypeError):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    messages.append({"role": "user", "content": user_message})

    if session['status'] == 'completed':
        return messages, "Давайте начнём сначала! Как вас зовут?", None, None, None

    try:
        ai_response = get_ai_response(messages)
    except Exception as e:
        ai_response = f"Извините, произошла ошибка: {e}"

    messages.append({"role": "assistant", "content": ai_response})

    keywords = ["карьерных трека", "треки", "трек", "**Трек" "рекомендации", "профессии", "варианты"]
    has_track_structure = bool(re.search(r'(Трек\s*\d+|^\d+\.\s*).*\n.*описание', ai_response, re.MULTILINE | re.IGNORECASE))
    if any(keyword in ai_response.lower() for keyword in keywords ) or has_track_structure:
        tracks = extract_tracks_from_ai_response(ai_response)
        review = extract_review_from_ai_response(ai_response)

        update_session_result(session_id, json.dumps(tracks, ensure_ascii=False), review)
        parent_code = generate_parent_code(session_id)

        update_session_status(session_id, 'completed')

        return messages, ai_response, tracks, review, parent_code

    try:
        update_session_messages(session_id, json.dumps(messages, ensure_ascii=False))
    except Exception as e:
        print(f"Ошибка сохранения сообщений: {e}")

    return messages, ai_response, None, None, None

def extract_tracks_from_ai_response(text):
    tracks = []
    lines = text.strip().split('\n')
    current_track = None
    track_pattern = re.compile(r'^(?:Трек\s*\d+|\d+\.\s*)(.+)', re.IGNORECASE)

    for line in lines:
        line = line.strip()
        match = track_pattern.match(line)
        if match:
            if current_track:
                tracks.append(current_track)
            current_track = {'title': match.group(1), 'description': ''}
        elif current_track and line:
            current_track['description'] += line + '\n'

    if current_track and current_track['description'].strip():
        tracks.append(current_track)

    return tracks if tracks else None


def extract_review_from_ai_response(text):
    return text.split('\n')[-1] if text else ""

def get_user_results(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return None, None
    session = get_active_session(user['id'])
    if not session or not session['result_tracks']:
        return None, None
    try:
        tracks = json.loads(session['result_tracks'])
    except:
        tracks = None
    review = session['result_review'] or ""
    return tracks, review



def get_parent_report(code):
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, s.result_tracks, s.result_review
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.parent_code = ?
        ''', (code,))
        row = cursor.fetchone()
        if row:
            return {k: row[k] for k in row.keys()}
    return None
