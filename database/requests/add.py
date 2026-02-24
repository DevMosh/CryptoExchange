from sqlalchemy import select

from database.connect import async_session
from database.models import User


async def add_user(user_id: int, username: str, email: str):
    async with async_session() as session:
        # Проверяем, есть ли уже такой пользователь (на всякий случай)
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar()

        if not user:
            new_user = User(
                user_id=user_id,
                username=username,
                email=email,  # <--- Сохраняем почту
                is_active=True
            )
            session.add(new_user)
            await session.commit()
            return True # Пользователь создан
        return False # Пользователь уже был