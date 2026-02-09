from database.connection import async_session_maker
from database.queries import DatabaseQueries

ROLE_PERMISSIONS = {
    'editor': ['add_material', 'edit_material', 'delete_material'],
    'user': ['search_material', 'request_material']
}

async def get_user_role(user_id: int) -> str:
    """Получение роли пользователя"""
    async with async_session_maker() as session:
        db = DatabaseQueries(session)
        user = await db.get_user(user_id)
        return user.role if user else 'user'

async def check_permission(user_id: int, action: str) -> bool:
    """Проверка прав доступа"""
    role = await get_user_role(user_id)
    return action in ROLE_PERMISSIONS.get(role, [])
