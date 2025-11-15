from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import logging

logger = logging.getLogger(__name__)

# Метрики Prometheus
video_processed_total = Counter(
    'video_processed_total',
    'Общее количество обработанных видео',
    ['status']
)

video_processing_duration_seconds = Histogram(
    'video_processing_duration_seconds',
    'Время обработки видео в секундах',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

video_errors_total = Counter(
    'video_errors_total',
    'Количество ошибок при обработке видео'
)

videos_in_queue = Gauge(
    'videos_in_queue',
    'Количество видео в очереди обработки'
)


def get_metrics():
    """Возвращает метрики в формате Prometheus"""
    return generate_latest()


def increment_video_processed(status: str):
    """Увеличивает счетчик обработанных видео"""
    video_processed_total.labels(status=status).inc()


def observe_processing_duration(duration_seconds: float):
    """Записывает время обработки видео"""
    video_processing_duration_seconds.observe(duration_seconds)


def increment_video_errors():
    """Увеличивает счетчик ошибок"""
    video_errors_total.inc()


def set_videos_in_queue(count: int):
    """Устанавливает количество видео в очереди"""
    videos_in_queue.set(count)

