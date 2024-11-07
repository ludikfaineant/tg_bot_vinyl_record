from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    telegram_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    album_videos = relationship("AlbumVideo", back_populates="user", cascade="all, delete-orphan")

class AlbumVideo(Base):  # Таблица для всех видео
    __tablename__ = "album_videos"
    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)  # Ссылка на telegram_id в User
    file_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    user = relationship("User", back_populates="album_videos")