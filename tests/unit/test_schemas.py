import pytest
from datetime import datetime
import uuid

from app.schemas import VideoAnalysisResponse, AnalyzeResponse, VideoAnalysisCreate
from app.models import VideoStatus


def test_video_analysis_create():
    """Тест создания VideoAnalysisCreate"""
    schema = VideoAnalysisCreate(filename="test.mp4")
    
    assert schema.filename == "test.mp4"


def test_video_analysis_create_validation():
    """Тест валидации VideoAnalysisCreate"""
    # Должна быть указана filename
    with pytest.raises(Exception):  # Pydantic validation error
        VideoAnalysisCreate()


def test_video_analysis_response_from_dict():
    """Тест создания VideoAnalysisResponse из словаря"""
    video_id = uuid.uuid4()
    upload_time = datetime.utcnow()
    analysis_time = datetime.utcnow()
    
    data = {
        "id": video_id,
        "filename": "test.mp4",
        "upload_time": upload_time,
        "analysis_time": analysis_time,
        "has_motion": True,
        "processing_duration_ms": 1000,
        "status": VideoStatus.COMPLETED,
        "error_message": None
    }
    
    response = VideoAnalysisResponse(**data)
    
    assert response.id == video_id
    assert response.filename == "test.mp4"
    assert response.upload_time == upload_time
    assert response.analysis_time == analysis_time
    assert response.has_motion is True
    assert response.processing_duration_ms == 1000
    assert response.status == VideoStatus.COMPLETED
    assert response.error_message is None


def test_video_analysis_response_minimal():
    """Тест VideoAnalysisResponse с минимальными данными"""
    video_id = uuid.uuid4()
    upload_time = datetime.utcnow()
    
    data = {
        "id": video_id,
        "filename": "test.mp4",
        "upload_time": upload_time,
        "status": VideoStatus.PENDING
    }
    
    response = VideoAnalysisResponse(**data)
    
    assert response.id == video_id
    assert response.filename == "test.mp4"
    assert response.upload_time == upload_time
    assert response.status == VideoStatus.PENDING
    assert response.analysis_time is None
    assert response.has_motion is None
    assert response.processing_duration_ms is None
    assert response.error_message is None


def test_video_analysis_response_with_error():
    """Тест VideoAnalysisResponse с ошибкой"""
    video_id = uuid.uuid4()
    upload_time = datetime.utcnow()
    
    data = {
        "id": video_id,
        "filename": "test.mp4",
        "upload_time": upload_time,
        "status": VideoStatus.FAILED,
        "error_message": "Ошибка обработки"
    }
    
    response = VideoAnalysisResponse(**data)
    
    assert response.status == VideoStatus.FAILED
    assert response.error_message == "Ошибка обработки"


def test_analyze_response():
    """Тест AnalyzeResponse"""
    video_id = uuid.uuid4()
    
    response = AnalyzeResponse(
        video_id=video_id,
        status="pending",
        message="Видео принято в обработку"
    )
    
    assert response.video_id == video_id
    assert response.status == "pending"
    assert response.message == "Видео принято в обработку"


def test_video_analysis_response_status_enum():
    """Тест VideoAnalysisResponse с разными статусами"""
    video_id = uuid.uuid4()
    upload_time = datetime.utcnow()
    
    for status in VideoStatus:
        data = {
            "id": video_id,
            "filename": "test.mp4",
            "upload_time": upload_time,
            "status": status
        }
        
        response = VideoAnalysisResponse(**data)
        assert response.status == status


def test_video_analysis_response_serialization():
    """Тест сериализации VideoAnalysisResponse в JSON"""
    video_id = uuid.uuid4()
    upload_time = datetime.utcnow()
    
    data = {
        "id": video_id,
        "filename": "test.mp4",
        "upload_time": upload_time,
        "status": VideoStatus.COMPLETED,
        "has_motion": True,
        "processing_duration_ms": 1000
    }
    
    response = VideoAnalysisResponse(**data)
    json_data = response.model_dump()
    
    assert str(json_data["id"]) == str(video_id)
    assert json_data["filename"] == "test.mp4"
    assert json_data["status"] == VideoStatus.COMPLETED
    assert json_data["has_motion"] is True
    assert json_data["processing_duration_ms"] == 1000


def test_video_analysis_response_uuid_validation():
    """Тест валидации UUID в VideoAnalysisResponse"""
    video_id = uuid.uuid4()
    upload_time = datetime.utcnow()
    
    # Валидный UUID
    data = {
        "id": video_id,
        "filename": "test.mp4",
        "upload_time": upload_time,
        "status": VideoStatus.PENDING
    }
    
    response = VideoAnalysisResponse(**data)
    assert response.id == video_id
    
    # Невалидный UUID должен вызвать ошибку
    with pytest.raises(Exception):
        data["id"] = "not-a-uuid"
        VideoAnalysisResponse(**data)


def test_analyze_response_required_fields():
    """Тест обязательных полей AnalyzeResponse"""
    video_id = uuid.uuid4()
    
    # Все поля обязательны
    response = AnalyzeResponse(
        video_id=video_id,
        status="pending",
        message="Видео принято в обработку"
    )
    
    assert response.video_id == video_id
    assert response.status == "pending"
    assert response.message == "Видео принято в обработку"
    
    # Отсутствие поля должно вызвать ошибку
    with pytest.raises(Exception):
        AnalyzeResponse(
            video_id=video_id,
            status="pending"
            # message отсутствует
        )

