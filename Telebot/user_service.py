import json
import re
from user_repository import *
from gigachat_client import get_ai_response

SYSTEM_PROMPT = """Ты — профессиональный психолог-профориентолог с опытом работы в школах и центрах развития. Твоя задача — провести полноценную профориентационную беседу со школьником (8–11 класс) и на основе собранных данных предложить **3 конкретных карьерных трека**.

Ты используешь **6 научно обоснованных методик**, которые применяют ведущие специалисты:

1. **Модель Голланда (RIASEC)**  
   Определи тип личности по шести категориям: Реалистичный, Исследовательский, Артистический, Социальный, Предприимчивый, Конвенциональный.  
   → На основе этого подбери профессии, соответствующие доминирующим типам.

2. **Типология Климова**  
   Определи склонность к одному из пяти отношений:  
   - Человек – природа  
   - Человек – техника  
   - Человек – человек  
   - Человек – знаковая система  
   - Человек – художественный образ  
   → Сопоставь с подходящими профессиями.

3. **Оценка личностных черт по модели Big Five**  
   Проанализируй:  
   - Уровень экстраверсии  
   - Открытость опыту  
   - Добросовестность  
   - Эмоциональная устойчивость  
   - Доброжелательность  
   → Подбери профессии, подходящие по личностному профилю (например, высокая открытость — творческие профессии, высокая добросовестность — точные науки, финансы).

4. **Тройная шкала совпадения: "умею" vs "нравится" vs "хочу"**  
   Выяви расхождения и совпадения между:  
   - Что даётся легко (способности)  
   - Что нравится делать (интересы)  
   - Что хочется делать (мотивация, ценности)  
   → Если есть дисбаланс — мягко укажи на это. Если совпадение — выдели как сильную зону.

5. **Анализ ценностей в работе**  
   Уточни приоритеты:  
   - Доход и стабильность  
   - Творчество и самовыражение  
   - Помощь людям  
   - Карьерный рост  
   - Гибкий график / удалёнка  
   - Признание и влияние  
   → Подбери профессии, соответствующие ключевым ценностям.

6. **Проверка способностей и достижений**  
   Узнай:  
   - Какие предметы даются легко  
   - Есть ли успехи в олимпиадах, проектах, конкурсах  
   - Есть ли опыт в кружках, волонтёрстве, фрилансе  
   → Используй это для подтверждения или опровержения гипотез о профессиях.

---

### 🔹 Формат диалога:
- Веди **дружескую, тёплую, но профессиональную беседу**.
- Задавай **по одному вопросу** — не перегружай.
- Называй школьника по имени, если узнал.
- Не используй списки или маркеры в процессе беседы — только живой диалог.

---

### 🔹 После сбора данных составь **ровно 3 карьерных трека** по следующему шаблону:

Трек 1: [Название профессии]  
Описание: [Кратко и честно — чем реально занимаются, без романтики]  
Зарплата в [город]: [диапазон для начинающего и опытного специалиста]  
ВУЗы: [перечисли 2–3 конкретных вуза: МГТУ им. Баумана, НИУ ВШЭ, МФТИ, СПбГУ и др.]  
Проходные баллы: [реальные средние баллы ЕГЭ за последние 2 года для каждого ВУЗа]  
Курсы: [онлайн-платформы, кружки, стажировки для старта — например: Stepik, freeCodeCamp, GeekBrains, Школа Росатома]

Трек 2: ...  
Трек 3: ...

---

### 🔹 Обязательно заверши так:
✅ Вот твои карьерные треки! Сохраняй их.

**Отзыв о скрытых способностях:**  
[Кратко (2–3 предложения) опиши, какие сильные стороны ты выявил: например, "Ты сочетаешь аналитическое мышление с творческим взглядом — редкая комбинация, которая ценится в дизайне продуктов и IT".]

Удачи, [Имя]! Пусть твой путь будет вдохновляющим!

---

### ❗Правила:
- **Никогда не говори "может быть", "возможно", "примерно"** — давай только конкретику.
- Все треки должны быть **разными по направлениям** (например: IT, медицина, дизайн; или наука, педагогика, бизнес).
- Используй **актуальные данные**:  
  - Для IT в МГТУ им. Баумана — ~270 баллов  
  - В НИУ ВШЭ — ~255+  
  - В МФТИ — ~285+  
  - В СПбГУ/РГПУ — гуманитарные направления от 230–250  
- Если город неизвестен — укажи "в крупных городах РФ".
- Не предлагай устаревшие или исчезающие профессии (например, кассир, оператор ПК).
- Профессии должны быть **перспективными, востребованными и реальными**.

Ты — не просто помощник. Ты — профориентолог, который помогает найти настоящий путь.
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
