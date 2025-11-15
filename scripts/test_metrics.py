#!/usr/bin/env python3
"""
Скрипт для тестирования метрик Prometheus.
Отправляет видео на анализ и проверяет, что метрики обновляются.
"""
import sys
import os
import time
import httpx
import cv2
import numpy as np
import tempfile

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def create_test_video(output_path: str, has_motion: bool = True, num_frames: int = 60):
    """Создает тестовое видео файл"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))
    
    if not out.isOpened():
        raise ValueError(f"Не удалось создать видео файл: {output_path}")
    
    for i in range(num_frames):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        if has_motion and i > 10:
            # Рисуем движущийся прямоугольник
            x = 100 + (i * 5)
            y = 100
            cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()
    print(f"✅ Создано тестовое видео: {output_path}")


def check_health():
    """Проверяет доступность API"""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
            response.raise_for_status()
            print(f"✅ API доступен: {response.json()}")
            return True
    except Exception as e:
        print(f"❌ API недоступен: {e}")
        return False


def get_metrics():
    """Получает метрики из /metrics endpoint"""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/metrics")
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"❌ Ошибка при получении метрик: {e}")
        return None


def parse_metric_value(metrics_text: str, metric_name: str) -> float:
    """Парсит значение метрики из текста Prometheus"""
    for line in metrics_text.split('\n'):
        if line.startswith(metric_name) and not line.startswith('#'):
            # Формат: metric_name{labels} value
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return float(parts[-1])
                except ValueError:
                    pass
    return 0.0


def send_video_for_analysis(video_path: str) -> str:
    """Отправляет видео на анализ и возвращает video_id"""
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{API_BASE_URL}/analyze",
                    files=files
                )
                response.raise_for_status()
                result = response.json()
                video_id = result['video_id']
                print(f"✅ Видео отправлено на анализ. ID: {video_id}")
                return video_id
    except Exception as e:
        print(f"❌ Ошибка при отправке видео: {e}")
        raise


def wait_for_processing(video_id: str, max_wait: int = 60) -> bool:
    """Ждет завершения обработки видео"""
    print(f"⏳ Ожидание обработки видео {video_id}...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{API_BASE_URL}/results/{video_id}")
                response.raise_for_status()
                result = response.json()
                status = result['status']
                
                if status == 'completed':
                    print(f"✅ Обработка завершена. Движение: {result.get('has_motion')}")
                    return True
                elif status == 'failed':
                    print(f"❌ Обработка завершилась с ошибкой: {result.get('error_message')}")
                    return False
                
                time.sleep(1)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print("⏳ Запись еще не создана, продолжаем ожидание...")
                time.sleep(1)
            else:
                raise
        except Exception as e:
            print(f"⚠️ Ошибка при проверке статуса: {e}")
            time.sleep(1)
    
    print(f"⏱️ Превышено время ожидания ({max_wait} секунд)")
    return False


def test_metrics():
    """Основная функция тестирования метрик"""
    print("=" * 60)
    print("Тестирование метрик Prometheus")
    print("=" * 60)
    
    # Проверяем доступность API
    if not check_health():
        print("❌ API недоступен. Убедитесь, что приложение запущено.")
        return False
    
    # Получаем начальные метрики
    print("\n📊 Получение начальных метрик...")
    initial_metrics = get_metrics()
    if not initial_metrics:
        print("❌ Не удалось получить метрики")
        return False
    
    initial_processed = parse_metric_value(initial_metrics, 'video_processed_total')
    initial_errors = parse_metric_value(initial_metrics, 'video_errors_total')
    initial_queue = parse_metric_value(initial_metrics, 'videos_in_queue')
    
    print(f"Начальные значения:")
    print(f"  - video_processed_total: {initial_processed}")
    print(f"  - video_errors_total: {initial_errors}")
    print(f"  - videos_in_queue: {initial_queue}")
    
    # Создаем тестовое видео
    print("\n🎬 Создание тестового видео...")
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        video_path = tmp_file.name
    
    try:
        create_test_video(video_path, has_motion=True)
        
        # Отправляем видео на анализ
        print("\n📤 Отправка видео на анализ...")
        video_id = send_video_for_analysis(video_path)
        
        # Ждем завершения обработки
        success = wait_for_processing(video_id, max_wait=60)
        
        if not success:
            print("❌ Обработка не завершилась успешно")
            return False
        
        # Ждем немного, чтобы метрики обновились
        print("\n⏳ Ожидание обновления метрик (5 секунд)...")
        time.sleep(5)
        
        # Получаем обновленные метрики
        print("\n📊 Получение обновленных метрик...")
        updated_metrics = get_metrics()
        if not updated_metrics:
            print("❌ Не удалось получить обновленные метрики")
            return False
        
        updated_processed = parse_metric_value(updated_metrics, 'video_processed_total')
        updated_errors = parse_metric_value(updated_metrics, 'video_errors_total')
        updated_queue = parse_metric_value(updated_metrics, 'videos_in_queue')
        
        print(f"\nОбновленные значения:")
        print(f"  - video_processed_total: {updated_processed}")
        print(f"  - video_errors_total: {updated_errors}")
        print(f"  - videos_in_queue: {updated_queue}")
        
        # Проверяем изменения
        print("\n🔍 Проверка изменений метрик...")
        success = True
        
        if updated_processed > initial_processed:
            print(f"✅ video_processed_total увеличился: {initial_processed} -> {updated_processed}")
        else:
            print(f"❌ video_processed_total не изменился: {initial_processed} -> {updated_processed}")
            success = False
        
        if updated_queue <= initial_queue:
            print(f"✅ videos_in_queue уменьшился или остался прежним: {initial_queue} -> {updated_queue}")
        else:
            print(f"⚠️ videos_in_queue увеличился: {initial_queue} -> {updated_queue}")
        
        # Проверяем наличие метрик в выводе
        print("\n📋 Проверка наличия всех метрик в выводе...")
        required_metrics = [
            'video_processed_total',
            'video_processing_duration_seconds',
            'video_errors_total',
            'videos_in_queue'
        ]
        
        for metric in required_metrics:
            if metric in updated_metrics:
                print(f"✅ Метрика {metric} найдена")
            else:
                print(f"❌ Метрика {metric} не найдена")
                success = False
        
        print("\n" + "=" * 60)
        if success:
            print("✅ Все проверки пройдены успешно!")
            print("\n💡 Теперь проверьте метрики в Prometheus UI:")
            print(f"   http://localhost:9090")
            print("\n   Попробуйте запросы:")
            print("   - video_processed_total")
            print("   - video_processing_duration_seconds")
            print("   - video_errors_total")
            print("   - videos_in_queue")
        else:
            print("❌ Некоторые проверки не пройдены")
        print("=" * 60)
        
        return success
        
    finally:
        # Удаляем временный файл
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"\n🧹 Удален временный файл: {video_path}")


if __name__ == "__main__":
    try:
        success = test_metrics()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

