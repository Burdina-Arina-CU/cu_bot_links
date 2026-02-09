from typing import List
from database.models import Material


def format_search_results(subject: str, lesson_type: str, teacher: str,
                          materials: List[Material], channel_link: str = None) -> str:
    """Форматирование результатов поиска по шаблону"""

    message = f"<b>{subject}</b>\n"
    message += f"<b>{lesson_type}</b>\n"
    message += f"<b>{teacher}</b>\n\n"

    # Группировка по неделям
    weeks_data = {}
    for mat in materials:
        if mat.week not in weeks_data:
            weeks_data[mat.week] = {'трансляция': None, 'запись': None}
        weeks_data[mat.week][mat.material_type] = {
            'link': mat.link,
            'date': mat.date
        }

    # Проверка: есть ли хоть один материал
    if not weeks_data:
        message += "<i>По выбранным фильтрам материалы не найдены</i>\n\n"
    else:
        # Сортировка недель
        for week in sorted(weeks_data.keys()):
            week_materials = weeks_data[week]

            # Проверка: есть ли хоть один непустой элемент
            has_content = any(
                week_materials.get(t) and week_materials[t]['link']
                for t in ['трансляция', 'запись']
            )

            if not has_content:
                continue

            message += f"<b>Неделя {week}</b>\n"

            # Трансляция
            broadcast = week_materials.get('трансляция')
            if broadcast and broadcast['date']:
                date_str = broadcast['date'].strftime('%d.%m.%Y')
                message += f"Трансляция {date_str}\n"
            else:
                message += "Трансляция\n"

            if broadcast and broadcast['link']:
                message += f"- {broadcast['link']}\n"
            else:
                message += "- пусто\n"

            # Запись
            record = week_materials.get('запись')
            if record and record['date']:
                date_str = record['date'].strftime('%d.%m.%Y')
                message += f"Запись {date_str}\n"
            else:
                message += "Запись\n"

            if record and record['link']:
                message += f"- {record['link']}\n\n"
            else:
                message += "- пусто\n\n"

    # Канал Telegram (всегда в конце)
    message += "<b>Тгк</b>\n"
    if channel_link:
        message += f"- {channel_link}"
    else:
        message += "- пусто"

    return message
