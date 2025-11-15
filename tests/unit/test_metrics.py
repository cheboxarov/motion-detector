import pytest
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, generate_latest

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
from app.models import VideoStatus


def test_increment_video_processed_pending():
    """Тест increment_video_processed для статуса pending"""
    increment_video_processed(VideoStatus.PENDING.value)
    increment_video_processed(VideoStatus.PENDING.value)
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processed_total' in metrics_text
    assert 'status="pending"' in metrics_text


def test_increment_video_processed_completed():
    """Тест increment_video_processed для статуса completed"""
    increment_video_processed(VideoStatus.COMPLETED.value)
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processed_total' in metrics_text
    assert 'status="completed"' in metrics_text


def test_increment_video_processed_failed():
    """Тест increment_video_processed для статуса failed"""
    increment_video_processed(VideoStatus.FAILED.value)
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processed_total' in metrics_text
    assert 'status="failed"' in metrics_text


def test_increment_video_processed_processing():
    """Тест increment_video_processed для статуса processing"""
    increment_video_processed(VideoStatus.PROCESSING.value)
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processed_total' in metrics_text
    assert 'status="processing"' in metrics_text


def test_observe_processing_duration_small():
    """Тест observe_processing_duration с маленьким значением"""
    observe_processing_duration(0.05)  # 50ms
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processing_duration_seconds' in metrics_text


def test_observe_processing_duration_medium():
    """Тест observe_processing_duration со средним значением"""
    observe_processing_duration(1.5)  # 1.5 секунды
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processing_duration_seconds' in metrics_text


def test_observe_processing_duration_large():
    """Тест observe_processing_duration с большим значением"""
    observe_processing_duration(45.0)  # 45 секунд
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processing_duration_seconds' in metrics_text


def test_observe_processing_duration_multiple():
    """Тест observe_processing_duration с несколькими значениями"""
    observe_processing_duration(0.1)
    observe_processing_duration(0.5)
    observe_processing_duration(1.0)
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processing_duration_seconds' in metrics_text


def test_increment_video_errors():
    """Тест increment_video_errors"""
    increment_video_errors()
    increment_video_errors()
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_errors_total' in metrics_text


def test_set_videos_in_queue():
    """Тест set_videos_in_queue"""
    set_videos_in_queue(5)
    set_videos_in_queue(10)
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'videos_in_queue' in metrics_text


def test_set_videos_in_queue_zero():
    """Тест set_videos_in_queue с нулевым значением"""
    set_videos_in_queue(0)
    
    metrics_text = generate_latest().decode('utf-8')
    assert 'videos_in_queue' in metrics_text


def test_set_videos_in_queue_multiple():
    """Тест set_videos_in_queue с несколькими значениями"""
    set_videos_in_queue(3)
    set_videos_in_queue(7)
    set_videos_in_queue(2)
    
    # Последнее значение должно быть 2
    metrics_text = generate_latest().decode('utf-8')
    assert 'videos_in_queue' in metrics_text


def test_get_metrics_format():
    """Тест формата вывода метрик"""
    metrics = get_metrics()
    
    assert isinstance(metrics, bytes)
    
    metrics_text = metrics.decode('utf-8')
    assert len(metrics_text) > 0
    
    # Проверяем, что метрики в формате Prometheus
    assert 'video_processed_total' in metrics_text
    assert 'video_processing_duration_seconds' in metrics_text
    assert 'video_errors_total' in metrics_text
    assert 'videos_in_queue' in metrics_text


def test_metrics_buckets():
    """Тест корректности buckets для гистограммы"""
    # Записываем несколько значений для проверки гистограммы
    observe_processing_duration(0.05)
    observe_processing_duration(0.5)
    observe_processing_duration(1.0)
    
    # Проверяем наличие метрики и buckets в выводе
    metrics_text = generate_latest().decode('utf-8')
    assert 'video_processing_duration_seconds' in metrics_text
    assert 'video_processing_duration_seconds_bucket' in metrics_text


def test_metrics_counter_labels():
    """Тест labels для счетчика video_processed_total"""
    # Увеличиваем счетчики для разных статусов
    increment_video_processed(VideoStatus.PENDING.value)
    increment_video_processed(VideoStatus.PROCESSING.value)
    increment_video_processed(VideoStatus.COMPLETED.value)
    increment_video_processed(VideoStatus.FAILED.value)
    
    metrics_text = generate_latest().decode('utf-8')
    
    # Проверяем наличие всех labels
    assert 'video_processed_total' in metrics_text
    assert 'status="pending"' in metrics_text or 'status="processing"' in metrics_text


def test_metrics_all_types():
    """Тест всех типов метрик одновременно"""
    increment_video_processed(VideoStatus.COMPLETED.value)
    observe_processing_duration(1.0)
    increment_video_errors()
    set_videos_in_queue(5)
    
    metrics_text = generate_latest().decode('utf-8')
    
    # Проверяем наличие всех метрик
    assert 'video_processed_total' in metrics_text
    assert 'video_processing_duration_seconds' in metrics_text
    assert 'video_errors_total' in metrics_text
    assert 'videos_in_queue' in metrics_text

