# 🚀 Быстрый старт для тестирования

## ⚡ Быстрая инструкция

### 1. Запуск Docker

**Убедитесь, что Docker запущен:**
- macOS: Откройте Docker Desktop и дождитесь полной загрузки
- Linux: `sudo systemctl start docker`

### 2. Запуск приложения

```bash
# Используйте скрипт запуска
./scripts/start.sh

# Или вручную
docker-compose -f docker/docker-compose.prod.yml --env-file .env.prod up -d --build
```

**Подождите 10-15 секунд** пока все сервисы запустятся.

### 3. Проверка статуса

```bash
docker-compose -f docker/docker-compose.prod.yml ps
```

Все сервисы должны быть в состоянии `Up (healthy)`.

---

## 🌐 Куда заходить

После запуска сервисы будут доступны:

| Сервис | URL | Что там |
|--------|-----|---------|
| **📡 API** | http://localhost:8000 | Основное приложение |
| **📚 API Docs (Swagger)** | http://localhost:8000/docs | **← СЮДА ДЛЯ ТЕСТИРОВАНИЯ!** |
| **📖 API Docs (ReDoc)** | http://localhost:8000/redoc | Альтернативная документация |
| **📊 Prometheus** | http://localhost:9090 | Метрики |
| **📈 Grafana** | http://localhost:3000 | Визуализация (admin/admin) |

---

## 🧪 Как тестировать

### Способ 1: Swagger UI (самый простой)

1. Откройте http://localhost:8000/docs
2. Разверните любой endpoint (например, `GET /health`)
3. Нажмите **"Try it out"**
4. Нажмите **Execute** ← Синяя кнопка
5. Смотрите результат внизу

**Для загрузки видео:**
1. Найдите `POST /analyze`
2. Нажмите `Try it out`
3. Нажмите `Choose File` и выберите видео файл (mp4, avi, etc.)
4. Нажмите `Execute`
5. Сохраните `video_id` из ответа
6. Используйте его в `GET /results/{video_id}`

### Способ 2: Postman

1. Откройте Postman
2. Импортируйте файл: **`docs/api/Postman_Collection_Video_Analysis.json`**
3. Убедитесь, что переменная `base_url` = `http://localhost:8000`
4. Используйте запросы из коллекции:
   - **Health Check** - проверка здоровья
   - **Get Metrics** - метрики Prometheus
   - **Upload Video for Analysis** - загрузите видео файл
   - **Get Analysis Result** - получите результат (использует сохраненный video_id)

### Способ 3: curl

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Метрики
curl http://localhost:8000/metrics

# 3. Загрузить видео (замените путь на реальный)
curl -X POST http://localhost:8000/analyze -F "file=@/path/to/video.mp4"

# 4. Получить результат (замените VIDEO_ID на реальный)
curl http://localhost:8000/results/VIDEO_ID
```

---

## 📝 Полный цикл тестирования

1. **Проверьте health:**
   ```bash
   curl http://localhost:8000/health
   ```
   Ожидаемый ответ: `{"status":"healthy","database":"connected"}`

2. **Загрузите видео:**
   ```bash
   curl -X POST http://localhost:8000/analyze -F "file=@test_video.mp4"
   ```
   Сохраните `video_id` из ответа!

3. **Подождите 5-10 секунд** (видео обрабатывается в фоне)

4. **Проверьте результат:**
   ```bash
   curl http://localhost:8000/results/ВАШ_VIDEO_ID
   ```

5. **Проверьте метрики в Prometheus:**
   - Откройте http://localhost:9090
   - В поиске введите: `video_processed_total`

---

## 🔍 Проверка логов

```bash
# Все логи
docker-compose -f docker/docker-compose.prod.yml logs -f

# Логи приложения
docker-compose -f docker/docker-compose.prod.yml logs -f app

# Логи PostgreSQL
docker-compose -f docker/docker-compose.prod.yml logs -f postgres
```

---

## 🛑 Остановка

```bash
docker-compose -f docker/docker-compose.prod.yml down
```

**Полная очистка (удаляет данные):**
```bash
docker-compose -f docker/docker-compose.prod.yml down -v
```

---

## ⚠️ Troubleshooting

### Docker не запущен
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

### Порт уже занят
Измените порты в `.env.prod`:
```bash
APP_PORT=8001
PROMETHEUS_PORT=9091
GRAFANA_PORT=3001
```

### Сервис не запускается
```bash
# Проверьте логи
docker-compose -f docker/docker-compose.prod.yml logs [service_name]

# Пересоберите
docker-compose -f docker/docker-compose.prod.yml build --no-cache

# Перезапустите
docker-compose -f docker/docker-compose.prod.yml up -d
```

---

## ✅ Быстрая проверка что все работает

```bash
# 1. Проверка health
curl http://localhost:8000/health

# 2. Проверка метрик
curl http://localhost:8000/metrics | head -20

# 3. Проверка статуса контейнеров
docker-compose -f docker/docker-compose.prod.yml ps
```

Все должно вернуть статус `200 OK` и контейнеры должны быть `Up (healthy)`.

---

**Удачного тестирования! 🎉**

