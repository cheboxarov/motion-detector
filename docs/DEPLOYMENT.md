# Инструкция по развертыванию

## Быстрый старт

### 1. Запуск всего стека (PostgreSQL + App + Prometheus + Grafana)

```bash
# Используйте скрипт запуска
./scripts/start_simple.sh

# Или вручную
docker-compose -f docker/docker-compose.yml up --build
```

Сервисы будут доступны:
- **App**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **PostgreSQL**: localhost:5432

### 2. Проверка endpoints

```bash
# Health check
curl http://localhost:8000/health

# Метрики
curl http://localhost:8000/metrics

# Загрузка видео
curl -X POST http://localhost:8000/analyze \
  -F "file=@test_video.mp4"

# Получение результата (замените VIDEO_ID на реальный ID)
curl http://localhost:8000/results/VIDEO_ID
```

## Запуск тестов

### Тесты с in-memory SQLite (быстрые)

```bash
source venv/bin/activate
pytest tests/ -v
```

### Тесты с реальной PostgreSQL из docker-compose

```bash
./scripts/run_tests_with_postgres.sh
```

Или вручную:

```bash
# Запуск PostgreSQL
docker-compose -f docker/docker-compose.yml up -d postgres

# Ожидание готовности
sleep 5

# Применение миграций
export DATABASE_URL="postgresql://video_user:video_password@localhost:5432/video_db"
source venv/bin/activate
alembic -c app/alembic.ini upgrade head

# Запуск тестов
pytest tests/ -v
```

## Структура endpoints

Все endpoints реальные (без фейковых данных):

1. **POST /analyze** - Загрузка видео для анализа
   - Принимает: multipart/form-data с файлом
   - Возвращает: `{video_id, status, message}`
   - Статус: `pending` → `processing` → `completed`/`failed`

2. **GET /results/{video_id}** - Получение результата анализа
   - Возвращает: полную информацию о видео и анализе
   - Статусы: `pending`, `processing`, `completed`, `failed`

3. **GET /metrics** - Prometheus метрики
   - Формат: Prometheus text format
   - Метрики: `video_processed_total`, `video_processing_duration_seconds`, `video_errors_total`, `videos_in_queue`

4. **GET /health** - Health check
   - Проверяет подключение к БД
   - Возвращает: `{status: "healthy", database: "connected"}`

## Проверка работоспособности

После запуска `docker-compose up` проверьте:

1. **App работает**: `curl http://localhost:8000/health`
   - Должен вернуть: `{"status":"healthy","database":"connected"}`

2. **Метрики доступны**: `curl http://localhost:8000/metrics`
   - Должен вернуть метрики в формате Prometheus

3. **Prometheus собирает метрики**: http://localhost:9090
   - В поиске: `video_processed_total`

4. **Grafana доступна**: http://localhost:3000
   - Логин: `admin`, Пароль: `admin`
   - Prometheus уже настроен как datasource

## Остановка

```bash
docker-compose -f docker/docker-compose.yml down
```

Для полной очистки (включая данные):

```bash
docker-compose -f docker/docker-compose.yml down -v
```

