from sqlalchemy import update, select

from database.connect import async_session
from database.models import User, Order


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


async def update_order_status(dexpay_order_id: str, new_status: str, tx_hash: str = None):
    """Обновляет статус заявки и сохраняет хэш транзакции (при выводе)"""
    async with async_session() as session:
        query = select(Order).where(Order.dexpay_order_id == dexpay_order_id)
        result = await session.execute(query)
        order = result.scalar()

        if order:
            order.status = new_status
            if tx_hash:
                order.tx_hash = tx_hash
            await session.commit()
            return order
        return None