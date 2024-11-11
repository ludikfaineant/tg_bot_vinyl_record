from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from settings import settings

engine = create_async_engine(settings.db.url)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
Base = declarative_base()


# Инициализация таблиц (выполнить при запуске)
def init_db():
    Base.metadata.create_all(bind=engine)
