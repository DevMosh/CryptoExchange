from sqlalchemy import update

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


async def set_user_dexpay_data(user_id: int, email: str, dexpay_internal_id: str):
    """Сохраняет email и внутренний ID Dexpay для верифицированного пользователя"""
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(
                email=email,
                dexpay_internal_id=dexpay_internal_id
            )
        )
        await session.commit()


async def set_user_kyc_status(user_id: int, status: str):
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.kyc_status = status
            await session.commit()
            return True
        return False