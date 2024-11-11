from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.database import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, unique=True, autoincrement=False
    )
    album_videos = relationship(
        "AlbumVideo", back_populates="user", cascade="all, delete-orphan"
    )
