from telebot import types
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def during_dialog_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⏸ Пауза", "🔄 Начать заново")
    return markup

def tracks_keyboard(n):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔐 Получить код для родителей", callback_data="parent_report"))
    markup.add(InlineKeyboardButton("🛠 Связаться с поддержкой", url="https://t.me/TrueWaySupport"))
    return markup

def info_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📘 Пример отчёта", callback_data="example"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_start"))
    return markup

def back_to_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 К началу", callback_data="back_start"))
    return markup

def admin_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    markup.add(InlineKeyboardButton("👥 Все пользователи", callback_data="admin_users"))
    return markup

def after_payment_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 Начать профориентацию", callback_data="start_session"))
    markup.add(InlineKeyboardButton("👤 Мои данные", callback_data="my_creds"))
    return markup
def main_keyboard():
    """Стартовая клавиатура (Inline)"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🎯 Узнать подробнее", callback_data="info"),
        types.InlineKeyboardButton("🚀 Начать профориентацию", callback_data="start_session")
    )
    return keyboard

def parent_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔑 Ввести код доступа", callback_data="enter_code"))
    keyboard.add(types.InlineKeyboardButton("🏠 В главное меню", callback_data="back_start"))
    return keyboard