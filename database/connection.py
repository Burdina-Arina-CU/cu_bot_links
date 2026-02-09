from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy import event, text
from config import DATABASE_URL
from .models import Base
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Используем QueuePool с настройками для автоматического переподключения [web:45][web:48]
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Отключаем verbose логи в продакшене
    poolclass=QueuePool,  # Пул с переиспользованием соединений
    pool_size=5,  # Минимум 5 постоянных соединений
    max_overflow=10,  # До 15 соединений при пиковой нагрузке
    pool_timeout=30,  # Таймаут ожидания соединения из пула
    pool_recycle=3600,  # Пересоздавать соединения каждый час (защита от stale connections)
    pool_pre_ping=True,  # КРИТИЧНО: проверка соединения перед использованием [web:48]
    connect_args={
        "server_settings": {"application_name": "telegram_bot"},
        "timeout": 10,  # Таймаут подключения к БД
        "command_timeout": 30,  # Таймаут выполнения команд
    } if 'postgresql' in DATABASE_URL else {}
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Отключаем автофлаш для контроля транзакций
)


async def get_db():
    """Получение сессии БД с автоматическим переподключением"""
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            async with async_session_maker() as session:
                yield session
                return
        except Exception as e:
            logger.error(f"Попытка {attempt + 1}/{max_retries} подключения к БД провалилась: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Экспоненциальная задержка
            else:
                raise


async def init_db():
    """Инициализация БД с retry-логикой и гарантией durability [web:47][web:50]"""
    max_retries = 5
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            logger.info(f"Попытка инициализации БД ({attempt + 1}/{max_retries})...")

            async with engine.begin() as conn:
                # Создание всех таблиц
                await conn.run_sync(Base.metadata.create_all)

                # Для PostgreSQL: включение WAL для durability [web:47][web:50]
                if 'postgresql' in DATABASE_URL:
                    await conn.execute(text("""
                        -- Гарантия durability: fsync после каждого commit
                        ALTER DATABASE telegram_bot SET synchronous_commit = 'on';
                    """))
                    logger.info("✅ PostgreSQL WAL настроен для максимальной надёжности")

            logger.info("✅ База данных успешно инициализирована")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД (попытка {attempt + 1}): {e}")

            if attempt < max_retries - 1:
                logger.info(f"⏳ Повтор через {retry_delay} сек...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Экспоненциальная задержка
            else:
                logger.error("❌ Не удалось инициализировать БД после всех попыток")
                logger.error("💡 Бот продолжит работу, но БД может быть недоступна")
                logger.error("💡 Проверьте подключение и перезапустите бота")
                return False


async def health_check():
    """Проверка здоровья БД для мониторинга"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False


async def close_db():
    """Корректное закрытие всех соединений"""
    logger.info("Закрытие пула соединений БД...")
    await engine.dispose()
    logger.info("✅ Все соединения закрыты")
