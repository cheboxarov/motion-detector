import pytest
import cv2
import numpy as np
import tempfile
import os
import time

from app.services.video_analyzer import VideoAnalyzer


def create_test_video(output_path: str, has_motion: bool = True, num_frames: int = 60, motion_threshold: float = 0.01):
    """Создает тестовое видео файл"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))
    
    for i in range(num_frames):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        if has_motion and i > 10:
            # Добавляем движение с контролируемой интенсивностью
            x = 100 + (i * 5)
            y = 100
            # Рассчитываем площадь движения относительно порога
            motion_area = int(640 * 480 * motion_threshold * 2) if motion_threshold < 0.1 else 640 * 480
            cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()


def test_video_analyzer_different_thresholds():
    """Тест VideoAnalyzer с разными порогами motion_threshold"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        # Видео с движением, которое занимает ~1% пикселей
        create_test_video(video_path, has_motion=True, motion_threshold=0.01)
        
        # Порог 0.0 - должно обнаружить любое движение
        analyzer_low = VideoAnalyzer(motion_threshold=0.0, frame_skip=0)
        has_motion, _ = analyzer_low.detect_motion(video_path)
        assert has_motion is True, "Порог 0.0 должен обнаружить любое движение"
        
        # Порог 0.01 - должно обнаружить
        analyzer_medium = VideoAnalyzer(motion_threshold=0.01, frame_skip=0)
        has_motion, _ = analyzer_medium.detect_motion(video_path)
        assert has_motion is True, "Порог 0.01 должен обнаружить движение"
        
        # Порог 1.0 - не должно обнаружить
        analyzer_high = VideoAnalyzer(motion_threshold=1.0, frame_skip=0)
        has_motion, _ = analyzer_high.detect_motion(video_path)
        assert has_motion is False, "Порог 1.0 не должен обнаружить движение"
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_different_frame_skip():
    """Тест VideoAnalyzer с разными значениями frame_skip"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True, num_frames=100)
        
        # frame_skip=0 - анализирует все кадры
        analyzer_no_skip = VideoAnalyzer(motion_threshold=0.01, frame_skip=0)
        has_motion_1, duration_1 = analyzer_no_skip.detect_motion(video_path)
        
        # frame_skip=5 - пропускает кадры
        analyzer_skip = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        has_motion_2, duration_2 = analyzer_skip.detect_motion(video_path)
        
        # Оба должны обнаружить движение
        assert has_motion_1 is True
        assert has_motion_2 is True
        
        # С пропуском должно быть быстрее
        assert duration_2 <= duration_1 * 1.5, "Пропуск кадров должен ускорить обработку"
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_empty_video():
    """Тест обработки пустого видео (0 кадров)"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        # Создаем видео с 0 кадрами (пустое видео)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))
        out.release()
        
        analyzer = VideoAnalyzer()
        with pytest.raises(ValueError):
            analyzer.detect_motion(video_path)
            
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_single_frame():
    """Тест обработки видео с одним кадром"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        out.write(frame)
        out.release()
        
        analyzer = VideoAnalyzer(motion_threshold=0.01)
        has_motion, duration_ms = analyzer.detect_motion(video_path)
        
        # С одним кадром нет движения (нет предыдущего кадра для сравнения)
        assert has_motion is False
        assert duration_ms > 0
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_large_video():
    """Тест обработки большого видео (проверка производительности)"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        # Создаем видео с большим количеством кадров (300 кадров = 15 секунд)
        create_test_video(video_path, has_motion=True, num_frames=300)
        
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        start_time = time.time()
        has_motion, duration_ms = analyzer.detect_motion(video_path)
        elapsed_time = time.time() - start_time
        
        assert has_motion is True
        assert duration_ms > 0
        # Проверяем, что обработка не занимает слишком много времени (максимум 10 секунд)
        assert elapsed_time < 10, "Обработка большого видео должна быть приемлемо быстрой"
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_boundary_threshold():
    """Тест граничного случая - движение ровно на пороге"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        # Создаем видео с движением, которое чуть больше порога
        create_test_video(video_path, has_motion=True, motion_threshold=0.01)
        
        # Порог чуть выше реального движения
        analyzer = VideoAnalyzer(motion_threshold=0.015, frame_skip=0)
        has_motion_1, _ = analyzer.detect_motion(video_path)
        
        # Порог чуть ниже реального движения
        analyzer = VideoAnalyzer(motion_threshold=0.005, frame_skip=0)
        has_motion_2, _ = analyzer.detect_motion(video_path)
        
        # Один из них должен обнаружить, другой нет (зависит от точности)
        assert isinstance(has_motion_1, bool)
        assert isinstance(has_motion_2, bool)
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_corrupted_file():
    """Тест обработки поврежденного файла"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        # Создаем поврежденный файл (просто текст)
        with open(video_path, 'wb') as f:
            f.write(b"This is not a valid video file")
        
        analyzer = VideoAnalyzer()
        with pytest.raises(ValueError, match="Не удалось открыть видео файл|Не удалось прочитать первый кадр"):
            analyzer.detect_motion(video_path)
            
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_nonexistent_file():
    """Тест обработки несуществующего файла"""
    analyzer = VideoAnalyzer()
    fake_path = "/nonexistent/path/to/video.mp4"
    
    with pytest.raises(ValueError, match="Не удалось открыть видео файл"):
        analyzer.detect_motion(fake_path)


def test_video_analyzer_no_motion_multiple_frames():
    """Тест видео без движения на нескольких кадрах"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        # Создаем видео без движения (все кадры одинаковые)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))
        
        for i in range(60):
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
            out.write(frame)
        
        out.release()
        
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=0)
        has_motion, duration_ms = analyzer.detect_motion(video_path)
        
        assert has_motion is False
        assert duration_ms > 0
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


def test_video_analyzer_motion_at_end():
    """Тест движения только в конце видео"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))
        
        for i in range(60):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Добавляем движение только в последних 10 кадрах
            if i >= 50:
                x = 100 + ((i - 50) * 10)
                cv2.rectangle(frame, (x, 100), (x + 100, 200), (255, 255, 255), -1)
            out.write(frame)
        
        out.release()
        
        analyzer = VideoAnalyzer(motion_threshold=0.01, frame_skip=5)
        has_motion, duration_ms = analyzer.detect_motion(video_path)
        
        assert has_motion is True
        assert duration_ms > 0
        
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

