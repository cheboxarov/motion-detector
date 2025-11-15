# Метрики Prometheus

Документация по метрикам, экспортируемым приложением Video Analysis Service.

## Доступные метрики

### video_processed_total

**Тип:** Counter  
**Описание:** Общее количество обработанных видео  
**Метки:**
- `status` - статус обработки: `completed`, `failed`

**Пример запроса в Prometheus:**
```promql
video_processed_total
```

**Пример запроса с фильтром:**
```promql
video_processed_total{status="completed"}
```

### video_processing_duration_seconds

**Тип:** Histogram  
**Описание:** Время обработки видео в секундах  
**Buckets:** `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]`

**Пример запроса в Prometheus:**
```promql
video_processing_duration_seconds
```

**Пример запроса для среднего времени обработки:**
```promql
rate(video_processing_duration_seconds_sum[5m]) / rate(video_processing_duration_seconds_count[5m])
```

**Пример запроса для 95-го перцентиля:**
```promql
histogram_quantile(0.95, rate(video_processing_duration_seconds_bucket[5m]))
```

### video_errors_total

**Тип:** Counter  
**Описание:** Количество ошибок при обработке видео

**Пример запроса в Prometheus:**
```promql
video_errors_total
```

**Пример запроса для скорости ошибок:**
```promql
rate(video_errors_total[5m])
```

### videos_in_queue

**Тип:** Gauge  
**Описание:** Текущее количество видео в очереди обработки (статусы `pending` или `processing`)

**Пример запроса в Prometheus:**
```promql
videos_in_queue
```

## Проверка метрик

### 1. Через API endpoint

Метрики доступны через HTTP endpoint `/metrics`:

```bash
curl http://localhost:8000/metrics
```

### 2. Через Prometheus UI

1. Откройте Prometheus UI: http://localhost:9090
2. Перейдите в раздел "Graph"
3. Введите запрос, например: `video_processed_total`
4. Нажмите "Execute"

### 3. Через тестовый скрипт

Используйте скрипт для автоматического тестирования метрик:

```bash
# Из контейнера
docker-compose -f docker/docker-compose.yml exec app python3 /app/scripts/test_metrics.py

# Или локально (если установлены зависимости)
python3 scripts/test_metrics.py
```

Скрипт:
- Проверяет доступность API
- Получает начальные метрики
- Отправляет тестовое видео на анализ
- Ждет завершения обработки
- Проверяет обновление метрик

## Примеры запросов для Grafana

### Количество обработанных видео за последний час

```promql
increase(video_processed_total[1h])
```

### Скорость обработки видео (видео/секунду)

```promql
rate(video_processed_total[5m])
```

### Процент успешных обработок

```promql
sum(rate(video_processed_total{status="completed"}[5m])) / sum(rate(video_processed_total[5m])) * 100
```

### Среднее время обработки

```promql
rate(video_processing_duration_seconds_sum[5m]) / rate(video_processing_duration_seconds_count[5m])
```

### Текущая очередь обработки

```promql
videos_in_queue
```

### Скорость ошибок

```promql
rate(video_errors_total[5m])
```

## Конфигурация Prometheus

Prometheus настроен на скрейпинг метрик каждые 15 секунд:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'video-analysis-service'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
```

## Troubleshooting

### Метрики не появляются в Prometheus

1. Проверьте, что приложение запущено и доступно:
   ```bash
   curl http://localhost:8000/health
   ```

2. Проверьте, что endpoint `/metrics` доступен:
   ```bash
   curl http://localhost:8000/metrics
   ```

3. Проверьте логи Prometheus:
   ```bash
   docker-compose -f docker/docker-compose.yml logs prometheus
   ```

4. Проверьте, что Prometheus может подключиться к приложению:
   ```bash
   docker-compose -f docker/docker-compose.yml exec prometheus wget -qO- http://app:8000/metrics
   ```

5. Убедитесь, что метрики генерируются (отправьте видео на анализ):
   ```bash
   docker-compose -f docker/docker-compose.yml exec app python3 /app/scripts/test_metrics.py
   ```

### Метрики не обновляются

Метрики обновляются только при обработке видео. Если метрики не видны:
- Отправьте видео на анализ через `/analyze` endpoint
- Дождитесь завершения обработки
- Проверьте метрики снова

### Метрики показывают только стандартные Python метрики

Это нормально, если видео еще не обрабатывались. Кастомные метрики (`video_processed_total`, `video_processing_duration_seconds`, и т.д.) создаются только при обработке видео.

Для генерации метрик используйте тестовый скрипт:
```bash
docker-compose -f docker/docker-compose.yml exec app python3 /app/scripts/test_metrics.py
```

