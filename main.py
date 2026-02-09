import asyncio
import signal
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.common import start_command, help_command
from handlers.admin_handlers import handle_admin_callbacks
from handlers.user_handlers import handle_user_callbacks, handle_user_text
from utils.scheduler import init_scheduler, shutdown_scheduler
from database.connection import init_db, close_db
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальная переменная для graceful shutdown
application = None


async def post_init(app: Application):
    """Инициализация с обработкой ошибок [web:47]"""
    db_ok = await init_db()
    if not db_ok:
        logger.warning("⚠️ БД недоступна, но бот запущен в ограниченном режиме")

    init_scheduler()
    logger.info("✅ Бот запущен и готов к работе")


async def post_shutdown(app: Application):
    """Корректное завершение с сохранением данных [web:50]"""
    logger.info("🛑 Начинается graceful shutdown...")

    shutdown_scheduler()
    await close_db()

    logger.info("✅ Все ресурсы освобождены, данные сохранены")


def signal_handler(signum, frame):
    """Обработка Ctrl+C и kill для graceful shutdown"""
    logger.info(f"Получен сигнал {signum}, завершение работы...")
    if application:
        asyncio.create_task(application.stop())


def main():
    global application

    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Создание приложения
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Обработчики callback
    application.add_handler(CallbackQueryHandler(
        handle_admin_callbacks,
        pattern=r'^add_.*'
    ))
    application.add_handler(CallbackQueryHandler(
        handle_user_callbacks,
        pattern=r'^(search|request)_.*'
    ))

    # Обработчики текста
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_user_text
    ))

    # Запуск с автоматическим перезапуском при ошибках сети
    logger.info("🚀 Запуск бота...")
    try:
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=False  # Не терять сообщения при рестарте
        )
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("👋 Бот остановлен")


if __name__ == '__main__':
    main()
