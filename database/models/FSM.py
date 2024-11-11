from sqlalchemy import BigInteger, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database.database import Base
from typing import Any


class StorageStateORM(Base):
    __tablename__ = "aiogram_states"  # type: ignore

    bot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    destiny: Mapped[str] = mapped_column(
        String(64), default="default", primary_key=True
    )

    state: Mapped[str] = mapped_column(String(64), nullable=True)


class StorageDataORM(Base):
    __tablename__ = "aiogram_data"  # type: ignore

    bot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    destiny = mapped_column(String(64), default="default", primary_key=True)

    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)
