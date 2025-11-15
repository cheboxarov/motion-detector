import pytest
import cv2
import numpy as np
import tempfile
import os

from app.services.video_analyzer import VideoAnalyzer


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


def test_video_analyzer_detect_motion_with_motion():
    """Тест детекции движения в видео с движением"""
    analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        has_motion, duration_ms = analyzer.detect_motion(video_path)
        
        assert has_motion is True
        assert duration_ms > 0
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_detect_motion_without_motion():
    """Тест детекции движения в видео без движения"""
    analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=False)
        has_motion, duration_ms = analyzer.detect_motion(video_path)
        
        assert has_motion is False
        assert duration_ms > 0
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_invalid_file():
    """Тест обработки невалидного видео файла"""
    analyzer = VideoAnalyzer()
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        tmp_file.write(b"This is not a valid video file")
        video_path = tmp_file.name
    
    try:
        with pytest.raises(ValueError):
            analyzer.detect_motion(video_path)
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

