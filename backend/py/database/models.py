from sqlalchemy import String, Float, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine



engine = create_async_engine(url = "sqlite+aiosqlite:////app/data/db.sqlite3")
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