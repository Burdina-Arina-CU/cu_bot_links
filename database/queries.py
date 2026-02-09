from sqlalchemy import select, delete, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, DBAPIError
from datetime import date
from .models import User, Material, TelegramChannelLink, UserRequest
import asyncio
import logging

logger = logging.getLogger(__name__)


def retry_on_db_error(max_retries=3, delay=1):
    """Декоратор для автоматического повтора при сбоях БД [web:45][web:48]"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, DBAPIError) as e:
                    last_exception = e
                    logger.warning(
                        f"БД недоступна (попытка {attempt + 1}/{max_retries}): {e}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # Экспоненциальная задержка
                        logger.info(f"Повторная попытка операции {func.__name__}...")
                    else:
                        logger.error(f"Операция {func.__name__} провалилась после {max_retries} попыток")

            raise last_exception

        return wrapper

    return decorator


class DatabaseQueries:
    def __init__(self, session: AsyncSession):
        self.session = session

    # === ПОЛЬЗОВАТЕЛИ ===

    @retry_on_db_error(max_retries=3, delay=1)
    async def get_user(self, user_id: int):
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @retry_on_db_error(max_retries=3, delay=1)
    async def create_user(self, user_id: int, username: str, role: str = 'user'):
        user = User(user_id=user_id, username=username, role=role)
        self.session.add(user)
        await self.session.commit()
        return user

    @retry_on_db_error(max_retries=3, delay=1)
    async def get_editors(self):
        result = await self.session.execute(
            select(User).where(User.role == 'editor')
        )
        return result.scalars().all()

    # === МАТЕРИАЛЫ ===

    @retry_on_db_error(max_retries=3, delay=1)
    async def insert_material(self, link: str, subject: str, lesson_type: str,
                              teacher: str, week: int, material_type: str,
                              date_val: date, created_by: int):
        """Атомарная вставка с гарантией сохранности [web:47]"""
        try:
            material = Material(
                link=link,
                subject=subject,
                lesson_type=lesson_type,
                teacher=teacher,
                week=week,
                material_type=material_type,
                date=date_val,
                created_by=created_by
            )
            self.session.add(material)
            await self.session.commit()
            logger.info(f"✅ Материал сохранён: {subject}/{lesson_type}/{teacher}/неделя {week}")
            return material
        except Exception as e:
            await self.session.rollback()  # Откат при ошибке
            logger.error(f"❌ Ошибка сохранения материала: {e}")
            raise

    @retry_on_db_error(max_retries=3, delay=1)
    async def get_materials(self, subject: str, lesson_type: str, teacher: str):
        result = await self.session.execute(
            select(Material).where(
                and_(
                    Material.subject == subject,
                    Material.lesson_type == lesson_type,
                    Material.teacher == teacher
                )
            ).order_by(Material.week)
        )
        return result.scalars().all()

    @retry_on_db_error(max_retries=3, delay=1)
    async def get_unique_subjects(self):
        result = await self.session.execute(
            select(Material.subject).distinct()
        )
        return [row[0] for row in result.all()]

    @retry_on_db_error(max_retries=3, delay=1)
    async def get_lesson_types_by_subject(self, subject: str):
        result = await self.session.execute(
            select(Material.lesson_type).where(
                Material.subject == subject
            ).distinct()
        )
        return [row[0] for row in result.all()]

    @retry_on_db_error(max_retries=3, delay=1)
    async def get_teachers(self, subject: str, lesson_type: str):
        result = await self.session.execute(
            select(Material.teacher).where(
                and_(
                    Material.subject == subject,
                    Material.lesson_type == lesson_type
                )
            ).distinct()
        )
        return [row[0] for row in result.all()]

    @retry_on_db_error(max_retries=5, delay=2)
    async def delete_old_broadcasts(self):
        """Удаление с retry-логикой для критичной операции [web:50]"""
        try:
            result = await self.session.execute(
                delete(Material).where(
                    and_(
                        Material.material_type == 'трансляция',
                        Material.date < date.today()
                    )
                )
            )
            await self.session.commit()
            deleted_count = result.rowcount
            logger.info(f"🗑 Удалено {deleted_count} устаревших трансляций")
            return deleted_count
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка при очистке трансляций: {e}")
            raise

    # === ССЫЛКИ НА КАНАЛЫ ===

    @retry_on_db_error(max_retries=3, delay=1)
    async def get_channel_link(self, subject: str, teacher: str):
        result = await self.session.execute(
            select(TelegramChannelLink.channel_link).where(
                and_(
                    TelegramChannelLink.subject == subject,
                    TelegramChannelLink.teacher == teacher
                )
            )
        )
        row = result.first()
        return row[0] if row else None

    # === ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ ===

    @retry_on_db_error(max_retries=3, delay=1)
    async def insert_request(self, user_id: int, request_text: str):
        try:
            request = UserRequest(user_id=user_id, request_text=request_text)
            self.session.add(request)
            await self.session.commit()
            return request
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка сохранения запроса: {e}")
            raise
