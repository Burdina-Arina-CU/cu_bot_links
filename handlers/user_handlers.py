from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.connection import async_session_maker
from database.queries import DatabaseQueries
from utils.formatters import format_search_results


async def handle_user_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик user callback"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == 'search_start':
        await search_step1_subject(query, context)
    elif data.startswith('search_subj_'):
        await search_step2_lesson_type(query, context)
    elif data.startswith('search_type_'):
        await search_step3_teacher(query, context)
    elif data.startswith('search_teach_'):
        await search_final(query, context)
    elif data == 'request_start':
        await request_start(query, context)


async def search_step1_subject(query, context):
    """Шаг 1: Выбор предмета"""
    async with async_session_maker() as session:
        db = DatabaseQueries(session)
        subjects = await db.get_unique_subjects()

    if not subjects:
        await query.edit_message_text('❌ В базе данных пока нет материалов')
        return

    keyboard = [[InlineKeyboardButton(subj, callback_data=f'search_subj_{subj}')]
                for subj in subjects]

    await query.edit_message_text(
        '📚 <b>Выберите предмет:</b>',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def search_step2_lesson_type(query, context):
    """Шаг 2: Выбор типа занятия"""
    subject = query.data.replace('search_subj_', '')
    context.user_data['search_subject'] = subject

    async with async_session_maker() as session:
        db = DatabaseQueries(session)
        lesson_types = await db.get_lesson_types_by_subject(subject)

    if not lesson_types:
        await query.edit_message_text(f'❌ Для предмета "{subject}" нет доступных типов занятий')
        return

    keyboard = [[InlineKeyboardButton(lt, callback_data=f'search_type_{lt}')]
                for lt in lesson_types]

    await query.edit_message_text(
        f'📖 <b>Выберите тип занятия</b>\n\nПредмет: <i>{subject}</i>',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def search_step3_teacher(query, context):
    """Шаг 3: Выбор преподавателя"""
    lesson_type = query.data.replace('search_type_', '')
    context.user_data['search_lesson_type'] = lesson_type

    subject = context.user_data['search_subject']

    async with async_session_maker() as session:
        db = DatabaseQueries(session)
        teachers = await db.get_teachers(subject, lesson_type)

    if not teachers:
        await query.edit_message_text(
            f'❌ Для предмета "{subject}" и типа "{lesson_type}" нет преподавателей'
        )
        return

    keyboard = [[InlineKeyboardButton(t, callback_data=f'search_teach_{t}')]
                for t in teachers]

    await query.edit_message_text(
        f'👨‍🏫 <b>Выберите преподавателя</b>\n\n'
        f'Предмет: <i>{subject}</i>\n'
        f'Тип: <i>{lesson_type}</i>',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def search_final(query, context):
    """Финальный шаг: Вывод результатов"""
    teacher = query.data.replace('search_teach_', '')

    subject = context.user_data['search_subject']
    lesson_type = context.user_data['search_lesson_type']

    async with async_session_maker() as session:
        db = DatabaseQueries(session)
        materials = await db.get_materials(subject, lesson_type, teacher)
        channel_link = await db.get_channel_link(subject, teacher)

    # Форматирование результатов
    formatted_message = format_search_results(
        subject, lesson_type, teacher, materials, channel_link
    )

    await query.edit_message_text(formatted_message, parse_mode='HTML')

    # Очистка данных
    context.user_data.pop('search_subject', None)
    context.user_data.pop('search_lesson_type', None)


async def request_start(query, context):
    """Начало запроса материала"""
    await query.edit_message_text(
        '💬 <b>Запрос материала</b>\n\n'
        'Опишите, какой материал вы не смогли найти.\n'
        'Ваш запрос будет отправлен администраторам.',
        parse_mode='HTML'
    )
    context.user_data['awaiting_request'] = True


async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от пользователей"""

    if context.user_data.get('awaiting_request'):
        request_text = update.message.text
        user_id = update.effective_user.id
        username = update.effective_user.username or "без username"

        # Сохранение запроса
        async with async_session_maker() as session:
            db = DatabaseQueries(session)
            await db.insert_request(user_id, request_text)

            # Уведомление редакторов
            editors = await db.get_editors()

            notification = f"""
🔔 <b>Новый запрос от пользователя</b>

👤 От: @{username}
ID: {user_id}
💬 Запрос: {request_text}
📅 Дата: {update.message.date.strftime('%d.%m.%Y %H:%M')}
"""

            for editor in editors:
                try:
                    await update.message.bot.send_message(
                        editor.user_id,
                        notification,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление редактору {editor.user_id}: {e}")

        await update.message.reply_text('✅ Ваш запрос отправлен администраторам!')
        context.user_data.pop('awaiting_request', None)
