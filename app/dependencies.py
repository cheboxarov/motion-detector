from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.video_analyzer import VideoAnalyzer


def get_video_analyzer() -> VideoAnalyzer:
    """Провайдер для VideoAnalyzer"""
    return VideoAnalyzer(motion_threshold=0.01, frame_skip=5)


def get_db_session() -> Session:
    """Провайдер для DB session"""
    return next(get_db())

