"""
Вспомогательный модуль для создания моделей, совместимых с SQLite
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy import TypeDecorator
import uuid
from datetime import datetime
import enum
import os

# Определяем, используем ли мы SQLite
USE_SQLITE = os.getenv("TEST_DB", "").startswith("sqlite") or "sqlite" in os.getenv("DATABASE_URL", "").lower()

if USE_SQLITE:
    # Для SQLite используем String вместо UUID
    UUIDType = String(36)
    EnumType = String(20)
else:
    UUIDType = PGUUID(as_uuid=True)
    EnumType = SQLEnum


class VideoStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Создаем модель, совместимую с SQLite
def create_video_analysis_model(Base):
    """Создает модель VideoAnalysis, совместимую с SQLite"""
    class VideoAnalysis(Base):
        __tablename__ = "video_analysis"

        id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
        filename = Column(String, nullable=False)
        upload_time = Column(DateTime, default=datetime.utcnow, nullable=False)
        analysis_time = Column(DateTime, nullable=True)
        has_motion = Column(Boolean, nullable=True)
        processing_duration_ms = Column(Integer, nullable=True)
        status = Column(EnumType if USE_SQLITE else SQLEnum(VideoStatus), default=VideoStatus.PENDING, nullable=False)
        error_message = Column(String, nullable=True)
    
    return VideoAnalysis

