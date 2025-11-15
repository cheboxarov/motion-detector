# Video Analysis Service

Микросервис для анализа видео и детекции движения. Принимает видеофайлы через REST API, анализирует их с помощью OpenCV и сохраняет результаты в PostgreSQL.

## Технологии

- Python 3.9+
- FastAPI
- SQLAlchemy + Alembic
- PostgreSQL
- OpenCV
- Prometheus метрики
- Docker / Docker Compose
- Pytest

## Возможности

- Загрузка видео файлов через REST API
- Детекция движения в видео с помощью OpenCV
- Сохранение результатов анализа в PostgreSQL
- Метрики Prometheus (количество обработанных видео, время обработки, ошибки)
- Health check endpoint
- Получение результатов анализа по ID

## Структура проекта

```
.
├── app/
│   ├── main.py              # FastAPI приложение
│   ├── models.py            # SQLAlchemy модели
│   ├── schemas.py           # Pydantic схемы
│   ├── database.py          # Конфигурация БД
│   ├── dependencies.py      # Провайдеры DI
│   ├── metrics.py           # Prometheus метрики
│   └── services/
│       └── video_analyzer.py # Логика анализа видео
│   ├── alembic/             # Миграции БД
│   └── alembic.ini          # Конфигурация Alembic
├── tests/                   # Тесты
├── docker/                   # Docker конфигурация
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── init.sql
├── docs/                     # Документация
│   ├── DEPLOYMENT.md
│   ├── PRODUCTION.md
│   ├── QUICK_START.md
│   ├── TROUBLESHOOTING.md
│   └── api/
│       └── Postman_Collection_Video_Analysis.json
├── scripts/                  # Скрипты запуска
│   ├── start.sh
│   ├── start_simple.sh
│   ├── test_endpoints.sh
│   └── run_tests_with_postgres.sh
└── requirements.txt
```

## Быстрый старт

### Запуск с Docker Compose (рекомендуется)

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd test2
```

2. Создайте файл `.env` (опционально, можно использовать значения по умолчанию):
```bash
cp .env.example .env
```

3. Запустите сервисы:
```bash
# Простой запуск (development)
./scripts/start_simple.sh

# Или production запуск
./scripts/start.sh

# Или вручную
docker-compose -f docker/docker-compose.yml up --build
```

4. Сервис будет доступен по адресу `http://localhost:8000`

5. Документация API доступна по адресу `http://localhost:8000/docs`

### Запуск без Docker

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Убедитесь, что PostgreSQL запущен и доступен

3. Создайте базу данных:
```bash
createdb video_db
```

4. Установите переменные окружения:
```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/video_db
```

5. Примените миграции:
```bash
alembic -c app/alembic.ini upgrade head
```

6. Запустите приложение:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Использование API

### Загрузка видео для анализа

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_video.mp4"
```

Ответ:
```json
{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Видео принято в обработку"
}
```

### Получение результата анализа

```bash
curl -X GET "http://localhost:8000/results/{video_id}" \
  -H "accept: application/json"
```

Ответ:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "your_video.mp4",
  "upload_time": "2024-01-01T12:00:00",
  "analysis_time": "2024-01-01T12:00:05",
  "has_motion": true,
  "processing_duration_ms": 5000,
  "status": "completed",
  "error_message": null
}
```

### Получение метрик Prometheus

```bash
curl -X GET "http://localhost:8000/metrics"
```

### Health check

```bash
curl -X GET "http://localhost:8000/health"
```

## Поддерживаемые форматы видео

- MP4 (.mp4)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- WebM (.webm)
- FLV (.flv)

## Миграции базы данных

### Создание новой миграции

```bash
alembic -c app/alembic.ini revision --autogenerate -m "Описание изменений"
```

### Применение миграций

```bash
alembic -c app/alembic.ini upgrade head
```

### Откат миграции

```bash
alembic -c app/alembic.ini downgrade -1
```

## Тестирование

Запуск тестов:
```bash
pytest
```

Запуск тестов с покрытием:
```bash
pytest --cov=app --cov-report=html
```

## Метрики Prometheus

Сервис предоставляет следующие метрики:

- `video_processed_total` - общее количество обработанных видео (по статусам)
- `video_processing_duration_seconds` - время обработки видео в секундах (гистограмма)
- `video_errors_total` - количество ошибок при обработке
- `videos_in_queue` - количество видео в очереди обработки

## Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| DATABASE_URL | URL подключения к PostgreSQL | postgresql://video_user:video_password@localhost:5432/video_db |
| POSTGRES_USER | Пользователь PostgreSQL | video_user |
| POSTGRES_PASSWORD | Пароль PostgreSQL | video_password |
| POSTGRES_DB | Имя базы данных | video_db |
| ENVIRONMENT | Окружение (development/production) | development |

## Алгоритм детекции движения

Сервис использует следующий алгоритм:

1. Видео разбивается на кадры
2. Каждый кадр конвертируется в grayscale
3. Вычисляется абсолютная разница между соседними кадрами
4. Применяется пороговая фильтрация (threshold)
5. Если доля измененных пикселей превышает порог (по умолчанию 1%) - движение обнаружено

Параметры можно настроить в `app/services/video_analyzer.py`:
- `motion_threshold` - порог для детекции движения (0.0 - 1.0)
- `frame_skip` - количество кадров для пропуска (для ускорения обработки)

## Структура базы данных

### Таблица `video_analysis`

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Уникальный идентификатор |
| filename | String | Имя загруженного файла |
| upload_time | DateTime | Время загрузки |
| analysis_time | DateTime | Время завершения анализа |
| has_motion | Boolean | Найдено ли движение |
| processing_duration_ms | Integer | Время обработки в миллисекундах |
| status | Enum | Статус: pending, processing, completed, failed |
| error_message | String | Сообщение об ошибке (если есть) |

## Разработка

### Установка зависимостей для разработки

```bash
pip install -r requirements.txt
```

### Линтинг и форматирование

```bash
# Установка дополнительных инструментов
pip install black flake8 mypy

# Форматирование
black app/ tests/

# Линтинг
flake8 app/ tests/

# Проверка типов
mypy app/
```

## Ограничения

- Максимальный размер загружаемого файла определяется настройками FastAPI/Uvicorn
- Обработка видео происходит асинхронно в фоновых задачах
- Для больших видео рекомендуется увеличить `frame_skip` для ускорения обработки

## Лицензия

MIT

