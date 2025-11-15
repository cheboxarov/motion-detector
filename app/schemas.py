from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid

from app.models import VideoStatus


class VideoAnalysisCreate(BaseModel):
    filename: str


class VideoAnalysisResponse(BaseModel):
    id: uuid.UUID
    filename: str
    upload_time: datetime
    analysis_time: Optional[datetime] = None
    has_motion: Optional[bool] = None
    processing_duration_ms: Optional[int] = None
    status: VideoStatus
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class AnalyzeResponse(BaseModel):
    video_id: uuid.UUID
    status: str
    message: str

