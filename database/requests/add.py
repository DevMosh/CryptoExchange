from sqlalchemy import select

from database.connect import async_session
from database.models import User

from database.connect import async_session
from database.models import User


async def add_user(user_id: int, username: str, email: str, dexpay_internal_id: str = None):
    async with async_session() as session:
        # Проверяем, нет ли уже такого пользователя на всякий случай
        user = await session.get(User, user_id)

        if not user:
            new_user = User(
                user_id=user_id,
                username=username,
                email=email,
                dexpay_internal_id=dexpay_internal_id
            )
            session.add(new_user)
        else:
            # Если пользователь существует, просто обновляем его данные
            user.email = email
            user.dexpay_internal_id = dexpay_internal_id

        await session.commit()