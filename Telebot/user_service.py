import json
import re
from user_repository import *
from gigachat_client import get_ai_response

SYSTEM_PROMPT = """
Ты — профессиональный психолог-профориентолог. Твоя задача — провести **диалог** со школьником (8–11 класс), чтобы собрать данные для построения **3 карьерных треков**.

❗Правило: **Сначала — только вопросы. Ни одной рекомендации, пока не собрано достаточно информации.**

---

### 🔹 Этап 1: Собери информацию (по одному вопросу за раз)
Задавай **по одному короткому вопросу**. Не перегружай.  
Используй тёплый, дружеский тон. Называй по имени, если узнал.

Узнай по очереди:
1. Имя
2. Класс и город
3. Школьный профиль (гуманитарный, технический и т.д.)
4. Хобби и увлечения (например, плавание)
5. Любимые предметы и что даётся легко
6. Участие в олимпиадах, проектах, кружках
7. Что нравится в работе: творчество, помощь, доход, стабильность, рост?
8. Личностные черты (через косвенные вопросы: "Тебе нравится работать в команде?" → экстраверсия)
9. Совпадают ли: «умею», «нравится», «хочу»? (Тройная шкала)
10. Какие профессии уже интересны?

→ Используй методики:
- Модель Голланда (RIASEC)
- Типология Климова
- Big Five (личностные черты)
- Анализ ценностей
- Проверка способностей
- Тройная шкала

Но **не упоминай их названия вслух** — просто применяй.

---

### 🔹 Этап 2: Дай результат (только после сбора данных)
Когда будет достаточно информации, составь **ровно 3 карьерных трека** по шаблону:

Трек 1: [Название профессии]  
Описание: [Чем реально занимаются, без романтики]  
Зарплата в [город]: [диапазон]  
ВУЗы: [конкретные вузы: МГТУ им. Баумана, ВШЭ, МФТИ и др.]  
Проходные баллы: [реальные средние баллы ЕГЭ]  
Курсы: [Stepik, freeCodeCamp, Фоксфорд и др.]

Трек 2: ...  
Трек 3: ...

✅ Вот твои карьерные треки! Сохраняй их.

**Отзыв о скрытых способностях:**  
[2–3 предложения: например, "Ты сочетаешь аналитическое мышление и эмпатию — это редкая комбинация, ценящаяся в UX-дизайне и медицине."]

Удачи, [Имя]! Пусть твой путь будет вдохновляющим!

---

### ❗Жёсткие правила:
- **Не давай советов до финала.**
- **Не предлагай профессии в процессе беседы.**
- **Не перечисляй варианты** (например, "можно стать врачом, тренером или журналистом").
- **Никаких "может быть", "примерно", "возможно"** — только конкретика.
- Все треки — **разные по направлениям** (IT, наука, творчество, медицина и т.д.).
- Используй актуальные данные: баллы ЕГЭ, зарплаты, вузы.
- Если город неизвестен — пиши "в крупных городах РФ".

Ты — профориентолог, а не генератор идей. Сначала слушай. Потом — действуй.
"""

def get_or_create_user(telegram_id):
    """Возвращает user_id и данные пользователя, при необходимости создаёт запись"""
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        create_user(telegram_id)
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

    if "✅ Вот твои карьерные треки!" in ai_response:
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
    track_pattern = re.compile(r'^Трек\s+\d+:\s*(.+)$', re.IGNORECASE)

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

    return tracks if len(tracks) >= 2 else (tracks + [{'title': 'Резервный трек', 'description': 'ИИ не вернул достаточно данных.'}] * (3 - len(tracks)))[:3]


def extract_review_from_ai_response(text):
    lines = text.strip().split('\n')
    review_starters = [
        "отзыв о скрытых способностях",
        "твой потенциал",
        "твои сильные стороны",
        "уникальные качества",
        "твои способности",
        "твой профиль",
        "анализ твоих качеств"
    ]
    
    for i, line in enumerate(lines):
        if any(starter in line.lower() for starter in review_starters):
            return "\n".join(lines[i:]).strip()
    return "\n".join(lines[-3:]).strip()

def get_user_results(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return None, None
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT result_tracks, result_review FROM sessions
            WHERE user_id = ? AND status = 'completed'
            ORDER BY completed_at DESC LIMIT 1
        ''', (user['id'],))
        row = cursor.fetchone()
        if not row:
            return None, None
        try:
            tracks = json.loads(row['result_tracks']) if row['result_tracks'] else None
        except:
            tracks = None
        review = row['result_review'] or ""
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