import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '8509701904:AAHHSIlHl6qa13YQc9-GWrjAvFw6VY4tAFk')

# === SQLite с файлом на диске (НЕ в памяти!) [web:43] ===
# Данные сохраняются даже после перезапуска бота
DATABASE_URL = "sqlite+aiosqlite:///./telegram_bot.db"  # ./ = текущая директория

# === PostgreSQL с защитой от потери данных [web:47][web:50] ===
# Раскомментируйте для продакшена:
# DB_CONFIG = {
#     'host': os.getenv('DB_HOST', 'localhost'),
#     'port': os.getenv('DB_PORT', '5432'),
#     'database': os.getenv('DB_NAME', 'telegram_bot'),
#     'user': os.getenv('DB_USER', 'postgres'),
#     'password': os.getenv('DB_PASSWORD', 'password')
# }
#
# DATABASE_URL = (
#     f"postgresql+asyncpg://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
#     f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
# )

# Настройки планировщика
CLEANUP_SCHEDULE = {
    'day_of_week': 'sun',
    'hour': 3,
    'minute': 0
}

DEFAULT_SUBJECTS = ["Матан", "Линал", "Дискра"]
DEFAULT_LESSON_TYPES = ["Семестр", "Лекция"]
DEFAULT_MATERIAL_TYPES = ["запись", "трансляция", "ссылка на канал препода"]
