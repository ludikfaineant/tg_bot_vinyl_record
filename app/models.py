from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    
class AlbumVideo(Base):  # Таблица для всех видео
    __tablename__ = "album_videos"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_path = Column(String ,nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    user = relationship("User")