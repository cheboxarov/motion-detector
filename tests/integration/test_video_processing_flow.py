import pytest
import cv2
import numpy as np
import tempfile
import os
import time
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import VideoAnalysis, VideoStatus
from app.main import app, process_video_analysis
from app.services.video_analyzer import VideoAnalyzer


def create_test_video(output_path: str, has_motion: bool = True):
    """Создает тестовое видео файл"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))
    
    for i in range(60):  # 3 секунды при 20 fps
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        if has_motion and i > 10:
            x = 100 + (i * 5)
            y = 100
            cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()


# Используем fixtures из conftest.py напрямую


def test_full_video_processing_flow_with_motion(client: TestClient, db_session: Session):
    """Полный цикл обработки видео с движением"""
    # Создаем тестовое видео
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        # 1. Загружаем видео
        with open(video_path, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        
        assert response.status_code == 200
        data = response.json()
        video_id = uuid.UUID(data["video_id"])
        assert data["status"] == VideoStatus.PENDING.value
        
        # 2. Проверяем, что запись создана в БД
        video_record = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        assert video_record is not None
        assert video_record.filename == "test_video.mp4"
        assert video_record.status == VideoStatus.PENDING
        
        # 3. Запускаем обработку вручную (симулируем фоновую задачу)
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        
        # Создаем временный файл для обработки
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(video_path):
            os.rename(video_path, temp_video_path)
        
        # Получаем DATABASE_URL для фоновой задачи
        from app.database import settings
        db_url = settings.database_url
        
        # Выполняем обработку с тестовой сессией
        process_video_analysis(video_id, temp_video_path, "test_video.mp4", db_url, analyzer, db_session=db_session)
        
        # 4. Проверяем результат
        db_session.refresh(video_record)
        assert video_record.status == VideoStatus.COMPLETED
        assert video_record.has_motion is True
        assert video_record.processing_duration_ms is not None
        assert video_record.processing_duration_ms > 0
        assert video_record.analysis_time is not None
        
        # 5. Получаем результат через API
        response = client.get(f"/results/{video_id}")
        assert response.status_code == 200
        result_data = response.json()
        assert result_data["status"] == VideoStatus.COMPLETED.value
        assert result_data["has_motion"] is True
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def test_full_video_processing_flow_without_motion(client: TestClient, db_session: Session):
    """Полный цикл обработки видео без движения"""
    # Создаем тестовое видео без движения
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=False)
        
        # Загружаем видео
        with open(video_path, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        
        assert response.status_code == 200
        data = response.json()
        video_id = uuid.UUID(data["video_id"])
        
        # Обрабатываем видео
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(video_path):
            os.rename(video_path, temp_video_path)
        
        from app.database import settings
        db_url = settings.database_url
        process_video_analysis(video_id, temp_video_path, "test_video.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем результат
        video_record = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        assert video_record.status == VideoStatus.COMPLETED
        assert video_record.has_motion is False
        
        # Получаем результат через API
        response = client.get(f"/results/{video_id}")
        assert response.status_code == 200
        result_data = response.json()
        assert result_data["has_motion"] is False
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def test_multiple_videos_processing(client: TestClient, db_session: Session):
    """Тест обработки нескольких видео подряд"""
    video_ids = []
    
    try:
        # Создаем и загружаем 3 видео
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                video_path = tmp_file.name
            
            create_test_video(video_path, has_motion=(i % 2 == 0))
            
            with open(video_path, "rb") as f:
                response = client.post(
                    "/analyze",
                    files={"file": (f"test_video_{i}.mp4", f, "video/mp4")}
                )
            
            assert response.status_code == 200
            data = response.json()
            video_id = uuid.UUID(data["video_id"])
            video_ids.append(video_id)
        
        # Обрабатываем все видео
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        from app.database import settings
        db_url = settings.database_url
        
        for i, video_id in enumerate(video_ids):
            # Файлы были сохранены через API в tempdir с именем {video_id}_{filename}
            temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video_{i}.mp4")
            # Если файл не найден, создаем тестовое видео заново
            if not os.path.exists(temp_video_path):
                create_test_video(temp_video_path, has_motion=(i % 2 == 0))
            if os.path.exists(temp_video_path):
                process_video_analysis(video_id, temp_video_path, f"test_video_{i}.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем, что все видео обработаны
        for video_id in video_ids:
            video_record = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
            assert video_record.status == VideoStatus.COMPLETED
            
            response = client.get(f"/results/{video_id}")
            assert response.status_code == 200
            
    finally:
        # Очистка временных файлов
        for i, video_id in enumerate(video_ids):
            temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video_{i}.mp4")
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)


def test_status_transition_pending_to_processing_to_completed(client: TestClient, db_session: Session):
    """Тест переходов статусов: pending -> processing -> completed"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        # Загружаем видео
        with open(video_path, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        
        video_id = uuid.UUID(response.json()["video_id"])
        video_record = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        
        # Проверяем начальный статус
        assert video_record.status == VideoStatus.PENDING
        
        # Симулируем обработку - меняем статус на processing
        video_record.status = VideoStatus.PROCESSING
        db_session.commit()
        db_session.refresh(video_record)
        assert video_record.status == VideoStatus.PROCESSING
        
        # Завершаем обработку
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        # Если файл не найден, создаем тестовое видео заново
        if not os.path.exists(temp_video_path):
            create_test_video(temp_video_path, has_motion=True)
        if os.path.exists(temp_video_path):
            from app.database import settings
            db_url = settings.database_url
            process_video_analysis(video_id, temp_video_path, "test_video.mp4", db_url, analyzer, db_session=db_session)
        
        db_session.refresh(video_record)
        assert video_record.status == VideoStatus.COMPLETED
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def test_invalid_video_processing_error(client: TestClient, db_session: Session):
    """Тест обработки ошибок при невалидном видео"""
    # Создаем невалидный файл
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
        tmp_file.write(b"This is not a valid video")
    
    try:
        # Пытаемся загрузить невалидный файл
        with open(video_path, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("invalid.mp4", f, "video/mp4")}
            )
        
        # Загрузка должна пройти, но обработка должна завершиться ошибкой
        assert response.status_code == 200
        video_id = uuid.UUID(response.json()["video_id"])
        
        # Симулируем обработку - должна завершиться ошибкой
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_invalid.mp4")
        if os.path.exists(video_path):
            os.rename(video_path, temp_video_path)
        
        from app.database import settings
        db_url = settings.database_url
        process_video_analysis(video_id, temp_video_path, "invalid.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем, что статус изменен на FAILED
        video_record = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        assert video_record.status == VideoStatus.FAILED
        assert video_record.error_message is not None
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_invalid.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def test_temp_file_cleanup_after_processing(client: TestClient, db_session: Session):
    """Тест очистки временных файлов после обработки"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        # Загружаем видео
        with open(video_path, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        
        video_id = uuid.UUID(response.json()["video_id"])
        
        # Обрабатываем видео
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(video_path):
            os.rename(video_path, temp_video_path)
        
        # Проверяем, что файл существует
        assert os.path.exists(temp_video_path)
        
        from app.database import settings
        db_url = settings.database_url
        process_video_analysis(video_id, temp_video_path, "test_video.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем, что файл удален после обработки
        assert not os.path.exists(temp_video_path), "Временный файл должен быть удален после обработки"
        
    finally:
        # Дополнительная очистка на случай ошибки
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

