import pytest
import cv2
import numpy as np
import tempfile
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import VideoAnalysis, VideoStatus
from app.main import process_video_analysis
from app.services.video_analyzer import VideoAnalyzer


# Используем fixture из conftest.py напрямую


def create_test_video(output_path: str, has_motion: bool = True):
    """Создает тестовое видео файл"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))
    
    if not out.isOpened():
        raise ValueError(f"Не удалось создать видео файл: {output_path}")
    
    for i in range(60):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        if has_motion and i > 10:
            x = 100 + (i * 5)
            y = 100
            cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()


def test_process_video_analysis_success(db_session: Session):
    """Тест успешного выполнения process_video_analysis"""
    # Создаем запись в БД
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Создаем тестовое видео
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        # Выполняем обработку
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        
        # Используем тестовую сессию для process_video_analysis
        from app.database import settings
        db_url = settings.database_url
        
        # Вызываем process_video_analysis с тестовой сессией
        process_video_analysis(video_id, video_path, "test.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем финальное состояние
        db_session.refresh(video)
        final_video = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        assert final_video is not None
        assert final_video.status == VideoStatus.COMPLETED
        assert final_video.has_motion is True
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_process_video_analysis_error_handling(db_session: Session):
    """Тест обработки ошибок в process_video_analysis"""
    # Создаем запись в БД
    video = VideoAnalysis(
        filename="invalid.mp4",
        status=VideoStatus.PENDING
    )
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Создаем невалидный файл
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
        tmp_file.write(b"This is not a valid video file")
    
    try:
        analyzer = VideoAnalyzer()
        
        # Выполняем обработку с ошибкой
        from app.database import settings
        db_url = settings.database_url
        
        # Вызываем process_video_analysis с тестовой сессией
        process_video_analysis(video_id, video_path, "invalid.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем, что статус изменен на FAILED
        db_session.refresh(video)
        final_video = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        assert final_video is not None
        assert final_video.status == VideoStatus.FAILED
        assert final_video.error_message is not None
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_process_video_analysis_status_updates(db_session: Session):
    """Тест обновления статусов во время обработки"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        
        from app.database import settings
        db_url = settings.database_url
        
        # Проверяем начальный статус
        db_session.refresh(video)
        assert video.status == VideoStatus.PENDING
        
        # Вызываем process_video_analysis - он сам обновит статусы
        process_video_analysis(video_id, video_path, "test.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем финальный статус
        db_session.refresh(video)
        assert video.status == VideoStatus.COMPLETED
        assert video.has_motion is True
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_process_video_analysis_nonexistent_video(db_session: Session):
    """Тест обработки несуществующего видео в БД"""
    fake_id = uuid.uuid4()
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        analyzer = VideoAnalyzer()
        
        # Выполняем обработку с несуществующим ID
        # Функция должна корректно обработать отсутствие записи
        from app.database import settings
        db_url = settings.database_url
        
        # Создаем пустую сессию для теста
        empty_db = db_session
        
        # Вызываем process_video_analysis с несуществующим ID
        process_video_analysis(fake_id, video_path, "test.mp4", db_url, analyzer, db_session=empty_db)
        
        # Проверяем, что файл был удален (функция удаляет файл в finally блоке)
        assert not os.path.exists(video_path)
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_process_video_analysis_temp_file_cleanup(db_session: Session):
    """Тест очистки временного файла после обработки"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        # Проверяем, что файл существует
        assert os.path.exists(video_path)
        
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        
        from app.database import settings
        db_url = settings.database_url
        
        # Вызываем process_video_analysis - он сам удалит файл
        process_video_analysis(video_id, video_path, "test.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем, что файл удален
        assert not os.path.exists(video_path)
        
    finally:
        # Дополнительная очистка на случай ошибки
        if os.path.exists(video_path):
            os.remove(video_path)


def test_process_video_analysis_db_session_closure(db_session: Session):
    """Тест корректности закрытия сессии БД"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        
        from app.database import settings
        db_url = settings.database_url
        
        # Проверяем, что сессия корректно работает
        assert db_session is not None
        
        # Вызываем process_video_analysis с тестовой сессией (не должна закрываться)
        process_video_analysis(video_id, video_path, "test.mp4", db_url, analyzer, db_session=db_session)
        
        # Проверяем, что сессия все еще работает (не закрыта)
        db_session.refresh(video)
        assert video.status == VideoStatus.COMPLETED
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

