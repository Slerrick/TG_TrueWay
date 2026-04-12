import json
from telebot import TeleBot, types
from config import ADMIN_IDS, HELP_TEXT, SUPPORT_LINK, INFO_TEXT, EXAMPLE_TRACK, WELCOME_TEXT
from keyboards import (
    main_keyboard, during_dialog_keyboard, tracks_keyboard,
    info_keyboard, back_to_main_keyboard, admin_keyboard,
    parent_keyboard, after_payment_keyboard
)
from user_service import (
    get_or_create_user, check_paid, simulate_payment, get_user_by_telegram_id,
    start_new_dialog, continue_dialog, add_user_message, get_user_results,
    get_active_session, update_session_status, generate_parent_code, get_parent_report
)
from user_repository import get_all_users, get_statistics, get_user_by_login
from database_manager import DatabaseManager
from gigachat_client import get_ai_response

db = DatabaseManager()

# Словарь состояний (логин, пароль, родительский код и т.д.)
user_states = {}


def register_handlers(bot: TeleBot):
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        get_or_create_user(message.from_user.id)
        bot.send_message(message.chat.id, WELCOME_TEXT, reply_markup=main_keyboard())

    @bot.message_handler(commands=['help'])
    def cmd_help(message):
        bot.send_message(message.chat.id, HELP_TEXT)

    @bot.message_handler(commands=['continue'])
    def cmd_continue(message):
        session, messages, err = continue_dialog(message.from_user.id)
        if err:
            bot.send_message(message.chat.id, err)
            return

    @bot.message_handler(commands=['myresults'])
    def cmd_myresults(message):
        tracks, review = get_user_results(message.from_user.id)
        if not tracks:
            bot.send_message(message.chat.id, "У вас пока нет завершённых профориентаций.")
            return
        for i, track in enumerate(tracks, 1):
            bot.send_message(
                message.chat.id,
                f"**Трек {i}: {track.get('title')}**\n{track.get('description')[:300]}...",
                parse_mode='Markdown'
            )
        bot.send_message(
            message.chat.id,
            f"**Отзыв о способностях:**\n{review}",
            parse_mode='Markdown'
        )

    @bot.message_handler(commands=['login'])
    def cmd_login(message):
        bot.send_message(message.chat.id, "Введите ваш логин:")
        user_states[message.chat.id] = {"state": "waiting_login"}

    @bot.message_handler(commands=['parent'])
    def cmd_parent(message):
        bot.send_message(message.chat.id, "Введите код доступа, который вы получили от ребёнка:", reply_markup=parent_keyboard())

    @bot.message_handler(commands=['support'])
    def cmd_support(message):
        bot.send_message(message.chat.id, f"Свяжитесь с нами: {SUPPORT_LINK}")

    @bot.message_handler(commands=['admin'])
    def cmd_admin(message):
        if message.from_user.id in ADMIN_IDS:
            bot.send_message(message.chat.id, "Панель администратора:", reply_markup=admin_keyboard())
        else:
            bot.send_message(message.chat.id, "Нет доступа.")

    # === Callback Handlers ===
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        try:
            if call.data == "info":
                bot.edit_message_text(
                    INFO_TEXT,
                    chat_id, call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=info_keyboard()
                )
            elif call.data == "example":
                bot.edit_message_text(
                    EXAMPLE_TRACK,
                    chat_id, call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=back_to_main_keyboard()
                )
            elif call.data == "buy":
                login, password = simulate_payment(user_id)
                bot.edit_message_text(
                    f"✅ Оплата прошла успешно!\n\n"
                    f"Ваши данные для входа:\n"
                    f"Логин: `{login}`\n"
                    f"Пароль: `{password}`\n"
                    f"Сохраните их.",
                    chat_id, call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=after_payment_keyboard()
                )
            elif call.data == "start_session":
                if not check_paid(user_id):
                    bot.answer_callback_query(call.id, "Сначала оплатите доступ.", show_alert=True)
                    user = get_user_by_telegram_id(user_id)
                    bot.send_message(
                chat_id,
                f"🔐 Ваши данные для входа:\n"
                f"Логин: `{user['login']}`\n"
                f"Пароль: `{user['password']}`\n\n"
                f"Сохраните их — вы сможете продолжить с любого устройства.",
                parse_mode='Markdown')
                session_id, err = start_new_dialog(user_id)
                if err:
                    bot.send_message(chat_id, err)
                    return
                bot.send_message(
                    chat_id,
                    "Диалог начат! Как тебя зовут?",
                    reply_markup=during_dialog_keyboard()
                )
            elif call.data == "back_start":
                bot.edit_message_text(WELCOME_TEXT, chat_id, call.message.message_id, reply_markup=main_keyboard())
            elif call.data == "my_creds":
                user = get_user_by_telegram_id(user_id)
                if user:
                    bot.send_message(
                        chat_id,
                        f"Ваши данные:\nЛогин: `{user['login']}`\nПароль: `{user['password']}`",
                        parse_mode='Markdown'
                    )
                else:
                    bot.send_message(chat_id, "Пользователь не найден.")
            elif call.data == "parent_mode":
                bot.edit_message_text("Режим родителя. Введите код доступа:", chat_id, call.message.message_id, reply_markup=parent_keyboard())
            elif call.data == "enter_code":
                bot.send_message(chat_id, "Введите код доступа (6 цифр):")
                user_states[chat_id] = {"state": "waiting_parent_code"}
            elif call.data == "admin_stats":
                if user_id in ADMIN_IDS:
                    total, paid, avg_len = get_statistics()
                    bot.send_message(
                        chat_id,
                        f"📊 Статистика:\n"
                        f"Всего пользователей: {total}\n"
                        f"Оплативших: {paid}\n"
                        f"Средняя длина диалога: {avg_len:.1f} сообщений"
                    )
                else:
                    bot.answer_callback_query(call.id, "Нет доступа")
            elif call.data == "admin_users":
                if user_id in ADMIN_IDS:
                    users = get_all_users()
                    text = "👥 Список пользователей:\n"
                    for u in users:
                        text += f"ID: {u['telegram_id']}, Логин: {u['login']}, Оплата: {'Да' if u['paid'] else 'Нет'}\n"
                    bot.send_message(chat_id, text)
                else:
                    bot.answer_callback_query(call.id, "Нет доступа")
            elif call.data.startswith("track_detail_"):
                try:
                    idx = int(call.data.split("_")[-1]) - 1
                    tracks, review = get_user_results(user_id)
                    if not tracks:
                        bot.send_message(chat_id, "У вас пока нет карьерных треков.")
                    elif 0 <= idx < len(tracks):
                        track = tracks[idx]
                        text = f"**{track.get('title', 'Без названия')}**\n\n"
                        desc = track.get('description', 'Нет описания.')
                        text += desc.replace("**", "").replace("•", "• ")
                        bot.send_message(chat_id, text, parse_mode='Markdown')
                    else:
                        bot.send_message(chat_id, "Такого трека нет.")
                except (ValueError, IndexError):
                    bot.send_message(chat_id, "Неверный номер трека.")
            elif call.data == "send_email":
                bot.send_message(chat_id, "Введите ваш email:")
                user_states[chat_id] = {"state": "waiting_email"}
            elif call.data == "parent_report":
                user = get_user_by_telegram_id(user_id)
                if not user:
                    bot.send_message(chat_id, "Сначала зарегистрируйтесь.")
                    return
                session = get_active_session(user['id'])
                if session and session['status'] == 'completed':
                    code = session['parent_code'] or generate_parent_code(session['id'])
                    bot.send_message(
                        chat_id,
                        f"🔐 Код доступа для родителя: `{code}`\nПередайте его родителю.",
                        parse_mode='Markdown'
                    )
                else:
                    bot.send_message(chat_id, "Сначала завершите профориентацию.")
            elif call.data == "ask_question":
                bot.send_message(chat_id, "Напишите ваш вопрос. Я передам его ИИ-ассистенту.")
                user_states[chat_id] = {"state": "waiting_question"}

        except Exception as e:
            bot.send_message(chat_id, f"Ошибка: {e}")
        finally:
            bot.answer_callback_query(call.id)

    # === State Handlers ===
    @bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("state") == "waiting_login")
    def process_login_input(message):
        login = message.text.strip()
        user_states.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "Теперь введите пароль:")
        user_states[message.chat.id] = {"state": "waiting_password", "login": login}

    @bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("state") == "waiting_password")
    def process_password_input(message):
        data = user_states.get(message.chat.id, {})
        login = data.get("login")
        password = message.text.strip()
        user = get_user_by_login(login)
        if user and user['password'] == password:
            with db.connect() as conn:
                conn.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (message.from_user.id, user['id']))
                conn.commit()
            bot.send_message(message.chat.id, "✅ Вход выполнен! Теперь вы можете начать профориентацию.")
        else:
            bot.send_message(message.chat.id, "❌ Неверный логин или пароль.")
        user_states.pop(message.chat.id, None)

    @bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("state") == "waiting_parent_code")
    def process_parent_code(message):
        code = message.text.strip()
        user_states.pop(message.chat.id, None)
        report = get_parent_report(code)
        if report:
            tracks = json.loads(report['result_tracks'])
            review = report['result_review']
            bot.send_message(message.chat.id, f"**Результаты ребёнка:**\n{review}")
            bot.send_message(message.chat.id, "**Карьерные треки:**")
            for i, t in enumerate(tracks, 1):
                bot.send_message(message.chat.id, f"{i}. {t.get('title')}\n{t.get('description')[:200]}...")
            bot.send_message(message.chat.id, "Вы можете задать вопросы ИИ о результатах ребёнка, нажав /ask_parent")
        else:
            bot.send_message(message.chat.id, "❌ Код не найден. Попробуйте ещё раз.", reply_markup=parent_keyboard())

    @bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("state") == "waiting_email")
    def process_email(message):
        email = message.text.strip()
        user_states.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "📧 Отправка отчёта на почту... (функция в разработке)")

    @bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("state") == "waiting_question")
    def process_question(message):
        question = message.text.strip()
        user_states.pop(message.chat.id, None)
        user = get_user_by_telegram_id(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "Пользователь не найден.")
            return
        session = get_active_session(user['id'])
        if not session or session['status'] != 'completed':
            bot.send_message(message.chat.id, "Сначала завершите профориентацию.")
            return
        try:
            messages = json.loads(session['messages'])
            history = [m for m in messages if m['role'] != 'system']
            history.append({"role": "user", "content": f"Пользователь спрашивает: {question}"})
            answer = get_ai_response(history)
        except Exception:
            answer = "Извините, произошла ошибка при обращении к ИИ."
        bot.send_message(message.chat.id, answer)

    # === Основной диалог ===
    @bot.message_handler(func=lambda m: True)
    def handle_dialog(message):
        user = get_user_by_telegram_id(message.from_user.id)
        if not user:
            user = get_or_create_user(message.from_user.id)
            if not user:
                bot.send_message(message.chat.id, "❌ Не удалось зарегистрировать вас. Напишите /start.")
                return

        session = get_active_session(user['id'])
        if not session:
            session_id, err = start_new_dialog(user['id'])
            if err:
                bot.send_message(message.chat.id, f"❌ Ошибка: {err}")
                return
            session = get_active_session(user['id'])
            bot.send_message(
            message.chat.id,
            "Диалог начат! Как тебя зовут?",
            reply_markup=during_dialog_keyboard()
        )
            return

        if session['status'] == 'completed':
            tracks, review = get_user_results(message.from_user.id)
            bot.send_message(
                message.chat.id,
                "Диалог уже завершён. Вот ваши результаты:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            if tracks:
                for i, track in enumerate(tracks, 1):
                    bot.send_message(
                        message.chat.id,
                        f"**Трек {i}: {track.get('title')}**\n{track.get('description')[:300]}...",
                        parse_mode='Markdown'
                    )
                bot.send_message(message.chat.id, "Выберите действие:", reply_markup=tracks_keyboard(len(tracks)))
            else:
                bot.send_message(message.chat.id, "Данные не найдены. Обратитесь в поддержку.")
            return

        # Управляющие команды
        if message.text == "⏸ Пауза":
            update_session_status(session['id'], 'paused')
            bot.send_message(
                message.chat.id,
                "Вы можете выйти и вернуться в любое время — диалог начнётся сначала.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return

        if message.text == "🔄 Начать заново":
            update_session_status(session['id'], 'aborted')
            start_new_dialog(message.from_user.id)
            bot.send_message(
                message.chat.id,
                "Диалог начат заново. Как тебя зовут?",
                reply_markup=during_dialog_keyboard()
            )
            return

        result = add_user_message(session['id'], message.text)
        new_messages, response, tracks, review, parent_code = result

        if not isinstance(new_messages, list):
            bot.send_message(message.chat.id, "❌ Ошибка при обработке сообщения.")
            return

        bot.send_message(message.chat.id, response, reply_markup=during_dialog_keyboard())

        if tracks is not None and isinstance(tracks, list) and len(tracks) > 0:
            from pdf_generator import PDFGenerator
            import os
            import re

            user_name = "Ученик"
            match = re.search(r'(зовут|тебя зовут)\s+([А-ЯЁ][а-яё]+)', response, re.IGNORECASE)
            if match:
                user_name = match.group(2)

            tracks_count = len(tracks)

            bot.send_message(
                message.chat.id,
                "🎉 Диалог завершён! Готовлю ваш персональный отчёт…",
                reply_markup=types.ReplyKeyboardRemove()
            )

            # Генерация PDF
            try:
                pdf_gen = PDFGenerator()
                pdf_path = os.path.join(os.path.dirname(__file__), f"report_{message.from_user.id}.pdf")
                pdf_gen.generate_report(tracks, review, user_name=user_name)
                pdf_gen.output(pdf_path)

                with open(pdf_path, 'rb') as pdf_file:
                    bot.send_document(
                        message.chat.id,
                        pdf_file,
                        caption="📄 Вот полный отчёт. Сохраните — он пригодится!"
                    )

                os.remove(pdf_path)  # очистка
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ Не удалось создать PDF: {e}")

            # Кнопки и код
            bot.send_message(message.chat.id, "Что дальше?", reply_markup=tracks_keyboard(tracks_count))
            if parent_code:
                bot.send_message(
                    message.chat.id,
                    f"🔐 Код для родителей: `{parent_code}`",
                    parse_mode='Markdown'
                )

            # Финал: завершаем сессию
            update_session_status(session['id'], 'completed')