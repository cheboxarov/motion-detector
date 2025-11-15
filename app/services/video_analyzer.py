import cv2
import os
import tempfile
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    Сервис для анализа видео и детекции движения
    """
    
    def __init__(self, motion_threshold: float = 0.01, frame_skip: int = 5):
        """
        Args:
            motion_threshold: Порог изменения пикселей для детекции движения (0.0 - 1.0)
            frame_skip: Количество кадров, которые пропускаются при анализе
        """
        self.motion_threshold = motion_threshold
        self.frame_skip = frame_skip
    
    def detect_motion(self, video_path: str) -> Tuple[bool, int]:
        """
        Детектирует движение в видео файле
        
        Args:
            video_path: Путь к видео файлу
            
        Returns:
            Tuple[bool, int]: (найдено ли движение, время обработки в миллисекундах)
        """
        import time
        start_time = time.time()
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise ValueError(f"Не удалось открыть видео файл: {video_path}")
            
            ret, prev_frame = cap.read()
            if not ret:
                cap.release()
                raise ValueError("Не удалось прочитать первый кадр видео")
            
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            frame_count = 0
            frames_analyzed = 0
            
            motion_detected = False
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Пропускаем кадры для ускорения обработки
                if frame_count % (self.frame_skip + 1) != 0:
                    continue
                
                frames_analyzed += 1
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Вычисляем разницу между кадрами
                frame_diff = cv2.absdiff(prev_gray, gray)
                
                # Применяем пороговую фильтрацию
                _, thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)
                
                # Посчитываем количество пикселей с движением
                motion_pixels = cv2.countNonZero(thresh)
                total_pixels = thresh.shape[0] * thresh.shape[1]
                motion_ratio = motion_pixels / total_pixels if total_pixels > 0 else 0
                
                # Если превышен порог - движение обнаружено
                # Анализируем минимум 10 кадров для более точного результата
                if motion_ratio > self.motion_threshold:
                    motion_detected = True
                    # Продолжаем анализ еще несколько кадров для подтверждения
                    if frames_analyzed >= 10:
                        break
                
                prev_gray = gray
            
            cap.release()
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Анализ завершен: движение={'обнаружено' if motion_detected else 'не обнаружено'}, "
                f"кадров проанализировано={frames_analyzed}, время={processing_time_ms}ms"
            )
            
            return motion_detected, processing_time_ms
            
        except Exception as e:
            logger.error(f"Ошибка при анализе видео: {str(e)}")
            raise

