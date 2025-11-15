from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.database import Base


class VideoStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoAnalysis(Base):
    __tablename__ = "video_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_time = Column(DateTime, nullable=True)
    has_motion = Column(Boolean, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    status = Column(SQLEnum(VideoStatus, native_enum=True, values_callable=lambda x: [e.value for e in VideoStatus], create_constraint=True), default=VideoStatus.PENDING, nullable=False, server_default='pending')
    error_message = Column(String, nullable=True)

