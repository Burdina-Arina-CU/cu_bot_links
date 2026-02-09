from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from config import DATABASE_URL, CLEANUP_SCHEDULE
from database.connection import async_session_maker
from database.queries import DatabaseQueries
import logging

logger = logging.getLogger(__name__)

# Сохранение задач в БД для восстановления после краша [web:23]
jobstores = {
    'default': SQLAlchemyJobStore(url=DATABASE_URL.replace('+asyncpg', '').replace('+aiosqlite', ''))
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    job_defaults={
        'coalesce': True,  # Пропускать накопившиеся задачи при downtime
        'max_instances': 1,  # Одна задача не может выполняться параллельно
        'misfire_grace_time': 3600  # Час на выполнение пропущенной задачи
    }
)


async def cleanup_old_broadcasts():
    """Очистка с обработкой ошибок БД"""
    try:
        async with async_session_maker() as session:
            db = DatabaseQueries(session)
            deleted_count = await db.delete_old_broadcasts()
            logger.info(f"🗑 Очистка завершена: удалено {deleted_count} трансляций")
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке трансляций: {e}")
        logger.error("💡 Очистка будет повторена на следующей неделе")


def init_scheduler():
    """Инициализация с восстановлением задач после краша [web:23]"""
    try:
        # Добавление задачи (replace_existing для восстановления)
        scheduler.add_job(
            cleanup_old_broadcasts,
            'cron',
            day_of_week=CLEANUP_SCHEDULE['day_of_week'],
            hour=CLEANUP_SCHEDULE['hour'],
            minute=CLEANUP_SCHEDULE['minute'],
            id='cleanup_broadcasts',
            replace_existing=True  # Важно для восстановления
        )

        scheduler.start()
        logger.info("⏰ Планировщик запущен (очистка: воскресенье 03:00)")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")


def shutdown_scheduler():
    """Корректное завершение планировщика"""
    try:
        scheduler.shutdown(wait=True)
        logger.info("⏰ Планировщик остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка остановки планировщика: {e}")
