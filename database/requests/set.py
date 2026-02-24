from database.connect import async_session
from database.models import User


async def set_user_active_status(user_id: int, status: bool = False):
    async with async_session() as session:
        # 1. Сначала находим пользователя по ID
        user = await session.get(User, user_id)

        if user:
            # 2. Просто меняем атрибут объекта
            user.is_active = status
            # 3. Сохраняем
            await session.commit()
            return True
        return False