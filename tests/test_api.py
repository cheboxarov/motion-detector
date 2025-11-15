import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import os
import tempfile
import cv2
import numpy as np

from app.models import VideoAnalysis, VideoStatus


def create_test_video(output_path: str, has_motion: bool = True):
    """Создает тестовое видео файл"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))
    
    for i in range(60):  # 3 секунды при 20 fps
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        if has_motion and i > 10:  # Добавляем движение после 10 кадра
            # Рисуем движущийся прямоугольник
            x = 100 + (i * 5)
            y = 100
            cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()


def test_health_check(client: TestClient):
    """Тест health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_metrics_endpoint(client: TestClient):
    """Тест metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "video_processed_total" in response.text


def test_upload_video(client: TestClient, tmp_path):
    """Тест загрузки видео файла"""
    # Создаем тестовое видео
    video_path = tmp_path / "test_video.mp4"
    create_test_video(str(video_path), has_motion=True)
    
    with open(video_path, "rb") as f:
        response = client.post(
            "/analyze",
            files={"file": ("test_video.mp4", f, "video/mp4")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "video_id" in data
    assert data["status"] == VideoStatus.PENDING.value
    assert data["message"] == "Видео принято в обработку"


def test_upload_invalid_file(client: TestClient, tmp_path):
    """Тест загрузки неверного формата файла"""
    # Создаем текстовый файл вместо видео
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is not a video file")
    
    with open(text_file, "rb") as f:
        response = client.post(
            "/analyze",
            files={"file": ("test.txt", f, "text/plain")}
        )
    
    assert response.status_code == 400
    assert "Неподдерживаемый формат файла" in response.json()["detail"]


def test_get_result_not_found(client: TestClient):
    """Тест получения несуществующего результата"""
    import uuid
    fake_id = uuid.uuid4()
    
    response = client.get(f"/results/{fake_id}")
    assert response.status_code == 404
    assert "не найдено" in response.json()["detail"]


def test_get_result(client: TestClient, db_session: Session):
    """Тест получения результата анализа"""
    # Создаем запись в БД
    video_record = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.COMPLETED,
        has_motion=True,
        processing_duration_ms=1000
    )
    db_session.add(video_record)
    db_session.commit()
    db_session.refresh(video_record)
    
    response = client.get(f"/results/{video_record.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(video_record.id)
    assert data["filename"] == "test.mp4"
    assert data["status"] == VideoStatus.COMPLETED.value
    assert data["has_motion"] is True

