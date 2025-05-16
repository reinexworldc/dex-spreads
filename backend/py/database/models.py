from sqlalchemy import String, Float, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
import os

# Определяем путь к базе данных в зависимости от окружения
def get_db_path():
    if os.path.exists('/app'):
        # Работаем в Docker
        return "sqlite+aiosqlite:////app/data/db.sqlite3"
    else:
        # Локальный запуск
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
        # Создаем директорию, если не существует
        os.makedirs(db_dir, exist_ok=True)
        # Формируем путь к файлу базы данных
        db_path = os.path.join(db_dir, 'db.sqlite3')
        return f"sqlite+aiosqlite:///{db_path}"

# Создаем движок базы данных с динамическим путем
engine = create_async_engine(url=get_db_path())
async_session = async_sessionmaker(engine)



class Base(AsyncAttrs, DeclarativeBase):
    pass



class Spread(Base):
    __tablename__ = "spreads"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    symbol: Mapped[str] = mapped_column(String(50))
    signal: Mapped[str] = mapped_column(String(50))
    backpack_price: Mapped[float] = mapped_column(Float)
    paradex_price: Mapped[float] = mapped_column(Float)
    hyperliquid_price: Mapped[float] = mapped_column(Float, default=0)
    created = mapped_column(BigInteger)
    exchange_pair: Mapped[str] = mapped_column(String(50), nullable=True)
    exchange1: Mapped[str] = mapped_column(String(50), nullable=True)
    exchange2: Mapped[str] = mapped_column(String(50), nullable=True)
    difference: Mapped[float] = mapped_column(Float, default=0)
    # Поля для сырых цен Paradex и размера контракта
    paradex_raw_price: Mapped[float] = mapped_column(Float, default=0)
    paradex_raw_bid: Mapped[float] = mapped_column(Float, default=0)
    paradex_raw_ask: Mapped[float] = mapped_column(Float, default=0)
    paradex_contract_size: Mapped[float] = mapped_column(Float, default=1.0)



async def db_async():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)