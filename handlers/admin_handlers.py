from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.connection import async_session_maker
from database.queries import DatabaseQueries
from config import DEFAULT_SUBJECTS, DEFAULT_LESSON_TYPES, DEFAULT_MATERIAL_TYPES
from datetime import datetime

# Состояния для добавления материала
ADD_SUBJECT, ADD_LESSON_TYPE, ADD_TEACHER, ADD_WEEK, ADD_MATERIAL_TYPE, ADD_DATE, ADD_LINK = range(7)


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех admin callback"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == 'add_start':
        await add_material_step1_subject(query, context)
    elif data.startswith('add_subj_'):
        await add_material_step2_lesson_type(query, context)
    elif data.startswith('add_type_'):
        await add_material_step3_teacher(query, context)
    elif data.startswith('add_teach_'):
        await add_material_step4_week(query, context)
    elif data.startswith('add_week_'):
        await add_material_step5_material_type(query, context)
    elif data.startswith('add_mtype_'):
        await add_material_step6_date(query, context)


async def add_material_step1_subject(query, context):
    """Шаг 1: Выбор предмета"""
    async with async_session_maker() as session:
        db = DatabaseQueries(session)
        subjects = await db.get_unique_subjects()

    if not subjects:
        subjects = DEFAULT_SUBJECTS

    keyboard = [[InlineKeyboardButton(subj, callback_data=f'add_subj_{subj}')]
                for subj in subjects]

    await query.edit_message_text(
        '📚 <b>Шаг 1/7:</b> Выберите предмет',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_material_step2_lesson_type(query, context):
    """Шаг 2: Выбор типа занятия"""
    subject = query.data.replace('add_subj_', '')
    context.user_data['add_subject'] = subject

    keyboard = [[InlineKeyboardButton(lt, callback_data=f'add_type_{lt}')]
                for lt in DEFAULT_LESSON_TYPES]

    await query.edit_message_text(
        f'📖 <b>Шаг 2/7:</b> Выберите тип занятия\n\n'
        f'Предмет: <i>{subject}</i>',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_material_step3_teacher(query, context):
    """Шаг 3: Ввод преподавателя"""
    lesson_type = query.data.replace('add_type_', '')
    context.user_data['add_lesson_type'] = lesson_type

    await query.edit_message_text(
        f'👨‍🏫 <b>Шаг 3/7:</b> Введите имя преподавателя\n\n'
        f'Предмет: <i>{context.user_data["add_subject"]}</i>\n'
        f'Тип: <i>{lesson_type}</i>',
        parse_mode='HTML'
    )
    context.user_data['awaiting_teacher'] = True


async def add_material_step4_week(query, context):
    """Шаг 4: Выбор недели"""
    keyboard = [
        [InlineKeyboardButton(f"Неделя {i}", callback_data=f'add_week_{i}')]
        for i in range(1, 16)
    ]

    await query.edit_message_text(
        f'📅 <b>Шаг 4/7:</b> Выберите номер недели',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_material_step5_material_type(query, context):
    """Шаг 5: Выбор типа материала"""
    week = int(query.data.replace('add_week_', ''))
    context.user_data['add_week'] = week

    keyboard = [[InlineKeyboardButton(mt, callback_data=f'add_mtype_{mt}')]
                for mt in DEFAULT_MATERIAL_TYPES]

    await query.edit_message_text(
        f'📦 <b>Шаг 5/7:</b> Выберите тип материала',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_material_step6_date(query, context):
    """Шаг 6: Ввод даты"""
    material_type = query.data.replace('add_mtype_', '')
    context.user_data['add_material_type'] = material_type

    await query.edit_message_text(
        f'📆 <b>Шаг 6/7:</b> Введите дату в формате ДД.ММ.ГГГГ\n\n'
        f'Например: 15.03.2026\n'
        f'Или отправьте "пропустить" если дата не нужна',
        parse_mode='HTML'
    )
    context.user_data['awaiting_date'] = True


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от админов"""

    # Обработка ввода преподавателя
    if context.user_data.get('awaiting_teacher'):
        context.user_data['add_teacher'] = update.message.text
        context.user_data['awaiting_teacher'] = False

        keyboard = [
            [InlineKeyboardButton(f"Неделя {i}", callback_data=f'add_week_{i}')]
            for i in range(1, 16)
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f'📅 <b>Шаг 4/7:</b> Выберите номер недели',
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    # Обработка ввода даты
    elif context.user_data.get('awaiting_date'):
        text = update.message.text.strip()

        if text.lower() == 'пропустить':
            context.user_data['add_date'] = None
        else:
            try:
                date_obj = datetime.strptime(text, '%d.%m.%Y').date()
                context.user_data['add_date'] = date_obj
            except ValueError:
                await update.message.reply_text(
                    '❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 15.03.2026)'
                )
                return

        context.user_data['awaiting_date'] = False
        await update.message.reply_text(
            f'🔗 <b>Шаг 7/7:</b> Введите ссылку на материал\n\n'
            f'Или отправьте "пропустить" если ссылки нет',
            parse_mode='HTML'
        )
        context.user_data['awaiting_link'] = True

    # Обработка ввода ссылки
    elif context.user_data.get('awaiting_link'):
        text = update.message.text.strip()
        link = None if text.lower() == 'пропустить' else text

        # Сохранение в БД
        async with async_session_maker() as session:
            db = DatabaseQueries(session)
            await db.insert_material(
                link=link,
                subject=context.user_data['add_subject'],
                lesson_type=context.user_data['add_lesson_type'],
                teacher=context.user_data['add_teacher'],
                week=context.user_data['add_week'],
                material_type=context.user_data['add_material_type'],
                date_val=context.user_data['add_date'],
                created_by=update.effective_user.id
            )

        await update.message.reply_text('✅ Материал успешно добавлен!')

        # Очистка данных
        keys_to_clear = ['add_subject', 'add_lesson_type', 'add_teacher',
                         'add_week', 'add_material_type', 'add_date', 'awaiting_link']
        for key in keys_to_clear:
            context.user_data.pop(key, None)
