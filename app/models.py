from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    processed_videos = relationship("ProcessedVideo", back_populates="owner", order_by="ProcessedVideo.created_at.desc()")

class ProcessedVideo(Base):
    __tablename__ = "processed_videos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_path = Column(String)
    created_at = Column(DateTime)  # Добавьте дату создания для хранения времени
    owner = relationship("User", back_populates="processed_videos")
