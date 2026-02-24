from sqlalchemy import select, func

from database.connect import async_session
from database.models import User


async def get_all_user_ids():
    """Возвращает список всех user_id"""
    async with async_session() as session:
        # SELECT user_id FROM users
        result = await session.scalars(select(User.user_id))
        return result.all()


async def get_all_users_active_ids():
    async with async_session() as session:
        result = await session.execute(select(User.user_id).where(User.is_active == True))
        return result.all()


async def get_user_count():
    async with async_session() as session:
        query = select(func.count(User.user_id))
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def get_user_active_count():
    async with async_session() as session:
        # Добавляем условие .where()
        query = (select(func.count(User.user_id)).where(User.is_active == True))
        result = await session.execute(query)
        return result.scalar()


async def get_user(user_id):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar()


async def check_email_exists(email: str) -> bool:
    """
    Проверяет, существует ли уже пользователь с таким email.
    Возвращает True, если почта занята, и False, если свободна.
    """
    async with async_session() as session:
        # Делаем выборку только одного поля (user_id) для оптимизации,
        # так как нам не нужен весь объект User.
        query = select(User.user_id).where(User.email == email).limit(1)

        result = await session.execute(query)

        # scalar_one_or_none вернет ID, если запись есть, или None, если нет.
        # Проверка `is not None` превратит это в булево значение.
        return result.scalar_one_or_none() is not None