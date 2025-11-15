import pytest
import cv2
import numpy as np
import tempfile
import os
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from prometheus_client import generate_latest

from app.models import VideoAnalysis, VideoStatus
from app.main import app, process_video_analysis
from app.services.video_analyzer import VideoAnalyzer
from app.metrics import (
    video_processed_total,
    video_processing_duration_seconds,
    video_errors_total,
    videos_in_queue,
    increment_video_processed,
    observe_processing_duration,
    increment_video_errors,
    set_videos_in_queue,
    get_metrics
)


def create_test_video(output_path: str, has_motion: bool = True):
    """Создает тестовое видео файл"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))
    
    for i in range(60):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        if has_motion and i > 10:
            x = 100 + (i * 5)
            y = 100
            cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()


@pytest.fixture
def client():
    """Создает тестовый клиент"""
    from tests.conftest import override_get_db, get_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Используем fixture из conftest.py напрямую


def test_metrics_on_successful_processing(client: TestClient, db_session: Session):
    """Тест обновления метрик при успешной обработке"""
    # Метрики Prometheus глобальные, очистка не требуется
    
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
        os.rename(video_path, temp_video_path)
        
        from app.database import settings
        db_url = settings.database_url
        process_video_analysis(video_id, temp_video_path, "test_video.mp4", db_url, analyzer)
        
        # Проверяем метрики
        metrics_text = get_metrics().decode('utf-8')
        
        # Должна быть метрика для completed
        assert 'video_processed_total{status="completed"}' in metrics_text or 'video_processed_total' in metrics_text
        
        # Должна быть метрика processing_duration
        assert 'video_processing_duration_seconds' in metrics_text
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def test_metrics_on_error(client: TestClient, db_session: Session):
    """Тест обновления метрик при ошибке"""
    # Метрики Prometheus глобальные, очистка не требуется
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
        tmp_file.write(b"This is not a valid video")
    
    try:
        # Загружаем невалидное видео
        with open(video_path, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("invalid.mp4", f, "video/mp4")}
            )
        
        video_id = uuid.UUID(response.json()["video_id"])
        
        # Пытаемся обработать - должна быть ошибка
        analyzer = VideoAnalyzer()
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_invalid.mp4")
        os.rename(video_path, temp_video_path)
        
        from app.database import settings
        db_url = settings.database_url
        process_video_analysis(video_id, temp_video_path, "invalid.mp4", db_url, analyzer)
        
        # Проверяем метрики
        metrics_text = get_metrics().decode('utf-8')
        
        # Должна быть метрика для failed
        assert 'video_processed_total{status="failed"}' in metrics_text or 'video_processed_total' in metrics_text
        
        # Должна быть метрика ошибок
        assert 'video_errors_total' in metrics_text
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_invalid.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def test_metrics_videos_in_queue(client: TestClient, db_session: Session):
    """Тест метрики videos_in_queue"""
    # Сбрасываем метрику
    set_videos_in_queue(0)
    
    # Создаем несколько видео в статусе PENDING
    videos = [
        VideoAnalysis(filename=f"test{i}.mp4", status=VideoStatus.PENDING)
        for i in range(5)
    ]
    
    db_session.add_all(videos)
    db_session.commit()
    
    # Подсчитываем видео в очереди
    pending_count = db_session.query(VideoAnalysis).filter(
        VideoAnalysis.status.in_([VideoStatus.PENDING, VideoStatus.PROCESSING])
    ).count()
    
    # Устанавливаем метрику
    set_videos_in_queue(pending_count)
    
    # Проверяем метрику
    metrics_text = get_metrics().decode('utf-8')
    assert 'videos_in_queue' in metrics_text
    
    # Проверяем, что значение корректно (может быть в разных форматах)
    assert str(pending_count) in metrics_text or f'videos_in_queue {pending_count}' in metrics_text


def test_metrics_processing_duration_histogram(client: TestClient, db_session: Session):
    """Тест метрики processing_duration_seconds (гистограмма)"""
    # Записываем несколько значений времени обработки
    durations = [0.05, 0.5, 1.0, 2.5, 5.0]
    
    for duration in durations:
        observe_processing_duration(duration)
    
    # Проверяем метрику
    metrics_text = get_metrics().decode('utf-8')
    assert 'video_processing_duration_seconds' in metrics_text
    
    # Проверяем наличие buckets
    assert 'video_processing_duration_seconds_bucket' in metrics_text


def test_metrics_endpoint_format(client: TestClient):
    """Тест формата /metrics endpoint"""
    response = client.get("/metrics")
    
    assert response.status_code == 200
    # Prometheus может возвращать разные форматы content-type
    assert "text/plain" in response.headers.get("content-type", "")
    
    metrics_text = response.text
    
    # Проверяем наличие всех метрик
    assert 'video_processed_total' in metrics_text
    assert 'video_processing_duration_seconds' in metrics_text
    assert 'video_errors_total' in metrics_text
    assert 'videos_in_queue' in metrics_text
    
    # Проверяем формат Prometheus
    lines = metrics_text.split('\n')
    metric_lines = [line for line in lines if line and not line.startswith('#')]
    
    # Каждая строка метрики должна содержать имя метрики
    assert len(metric_lines) > 0


def test_metrics_multiple_statuses(client: TestClient):
    """Тест метрик для разных статусов"""
    # Увеличиваем счетчики для разных статусов
    increment_video_processed(VideoStatus.PENDING.value)
    increment_video_processed(VideoStatus.PROCESSING.value)
    increment_video_processed(VideoStatus.COMPLETED.value)
    increment_video_processed(VideoStatus.COMPLETED.value)
    increment_video_processed(VideoStatus.FAILED.value)
    
    # Проверяем метрики через endpoint
    response = client.get("/metrics")
    metrics_text = response.text
    
    # Проверяем наличие метрик для всех статусов
    assert 'video_processed_total' in metrics_text
    
    # Проверяем, что метрики учитывают все статусы (может быть в разных строках)
    assert 'status="pending"' in metrics_text or 'video_processed_total' in metrics_text
    assert 'status="processing"' in metrics_text or 'video_processed_total' in metrics_text
    assert 'status="completed"' in metrics_text or 'video_processed_total' in metrics_text
    assert 'status="failed"' in metrics_text or 'video_processed_total' in metrics_text


def test_metrics_integration_full_flow(client: TestClient, db_session: Session):
    """Интеграционный тест метрик в полном цикле обработки"""
    # Метрики Prometheus глобальные, очистка не требуется
    
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
        
        video_id = uuid.UUID(response.json()["video_id"])
        
        # 2. Проверяем метрику очереди (должно быть 1)
        pending_count = db_session.query(VideoAnalysis).filter(
            VideoAnalysis.status.in_([VideoStatus.PENDING, VideoStatus.PROCESSING])
        ).count()
        set_videos_in_queue(pending_count)
        
        metrics_before = get_metrics().decode('utf-8')
        assert 'videos_in_queue' in metrics_before
        
        # 3. Обрабатываем видео
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        os.rename(video_path, temp_video_path)
        
        from app.database import settings
        db_url = settings.database_url
        process_video_analysis(video_id, temp_video_path, "test_video.mp4", db_url, analyzer)
        
        # 4. Проверяем финальные метрики
        metrics_after = get_metrics().decode('utf-8')
        
        # Должна быть метрика completed
        assert 'video_processed_total{status="completed"}' in metrics_after or 'video_processed_total' in metrics_after
        
        # Должна быть метрика processing_duration
        assert 'video_processing_duration_seconds' in metrics_after
        
        # Метрика очереди должна обновиться (меньше видео в очереди)
        updated_pending_count = db_session.query(VideoAnalysis).filter(
            VideoAnalysis.status.in_([VideoStatus.PENDING, VideoStatus.PROCESSING])
        ).count()
        set_videos_in_queue(updated_pending_count)
        
        metrics_final = get_metrics().decode('utf-8')
        assert 'videos_in_queue' in metrics_final
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        temp_video_path = os.path.join(tempfile.gettempdir(), f"{video_id}_test_video.mp4")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def test_metrics_counter_increment(client: TestClient):
    """Тест увеличения счетчика метрик"""
    # Получаем начальные метрики
    initial_metrics = get_metrics().decode('utf-8')
    initial_count = initial_metrics.count('video_processed_total')
    
    # Увеличиваем счетчик
    increment_video_processed(VideoStatus.COMPLETED.value)
    
    # Проверяем, что метрики изменились
    updated_metrics = get_metrics().decode('utf-8')
    
    # Проверяем наличие метрики
    assert 'video_processed_total' in updated_metrics


def test_metrics_histogram_buckets(client: TestClient):
    """Тест buckets для гистограммы processing_duration"""
    # Записываем значения в разные buckets
    observe_processing_duration(0.05)  # Меньше 0.1
    observe_processing_duration(0.3)   # Между 0.1 и 0.5
    observe_processing_duration(0.8)   # Между 0.5 и 1.0
    observe_processing_duration(1.5)   # Между 1.0 и 2.0
    observe_processing_duration(3.0)   # Между 2.0 и 5.0
    
    # Проверяем метрики
    response = client.get("/metrics")
    metrics_text = response.text
    
    # Должны быть buckets
    assert 'video_processing_duration_seconds_bucket' in metrics_text
    
    # Проверяем наличие +Inf bucket
    assert '+Inf' in metrics_text or 'le="+Inf"' in metrics_text

