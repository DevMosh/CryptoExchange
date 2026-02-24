import os
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from database.models import Base, User  # <--- ВАЖНО! Импорт модели User
from sqlalchemy import event

# Настраиваем путь. Файл database.db будет лежать в папке Database
DB_PATH = os.path.join("Database", "database.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Создаем движок
engine = create_async_engine(DATABASE_URL, echo=True)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

# Создаем фабрику сессий
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def create_tables():
    """Создает таблицы. Благодаря импорту User выше, Base знает про таблицу users."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)