from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.permissions import get_user_role
from database.connection import async_session_maker
from database.queries import DatabaseQueries


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое меню с выбором роли"""
    user_id = update.effective_user.id
    username = update.effective_user.username

    async with async_session_maker() as session:
        db = DatabaseQueries(session)
        user = await db.get_user(user_id)

        # Регистрация нового пользователя
        if not user:
            user = await db.create_user(user_id, username, role='user')

        role = user.role

    if role == 'editor':
        keyboard = [
            [InlineKeyboardButton("➕ Добавить материал", callback_data='add_start')],
            [InlineKeyboardButton("✏️ Редактировать материал", callback_data='edit_start')],
            [InlineKeyboardButton("🗑 Удалить материал", callback_data='delete_start')]
        ]
        message = "🔧 <b>Меню редактора</b>\n\nВыберите действие:"
    else:
        keyboard = [
            [InlineKeyboardButton("🔍 Найти материал", callback_data='search_start')],
            [InlineKeyboardButton("💬 Запросить материал", callback_data='request_start')]
        ]
        message = "👋 <b>Добро пожаловать!</b>\n\nВыберите действие:"

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    help_text = """
<b>Доступные команды:</b>

/start - Главное меню
/help - Справка

<b>Навигация:</b>
Используйте кнопки для взаимодействия с ботом.
"""
    await update.message.reply_text(help_text, parse_mode='HTML')
