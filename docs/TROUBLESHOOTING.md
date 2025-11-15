# 🔧 Troubleshooting - Решение проблем

## Проблема: Docker не запущен

**Ошибка:**
```
Cannot connect to the Docker daemon at unix:///Users/apple/.docker/run/docker.sock
```

**Решение:**
1. Откройте Docker Desktop
2. Дождитесь полной загрузки (зеленый индикатор вверху)
3. Попробуйте снова

**Проверка:**
```bash
docker ps
```
Должен показать список контейнеров или пустой список (но не ошибку).

---

## Проблема: Переменные окружения не читаются

**Ошибка:**
```
The "POSTGRES_USER" variable is not set. Defaulting to a blank string.
```

**Решение 1: Используйте простой docker-compose.yml**
```bash
./scripts/start_simple.sh
```

**Решение 2: Проверьте .env.prod**
```bash
cat .env.prod
```

Если файла нет, создайте:
```bash
cat > .env.prod << 'EOF'
POSTGRES_USER=video_user
POSTGRES_PASSWORD=video_password
POSTGRES_DB=video_db
POSTGRES_PORT=5432

APP_PORT=8000

PROMETHEUS_PORT=9090

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
GRAFANA_ROOT_URL=http://localhost:3000
EOF
```

**Решение 3: Используйте обычный docker-compose.yml**
```bash
docker-compose -f docker/docker-compose.yml up -d --build
```

---

## Проблема: Порт уже занят

**Ошибка:**
```
Error: bind: address already in use
```

**Решение:**
1. Найдите процесс на порту:
```bash
# macOS
lsof -i :8000

# Linux
sudo netstat -tulpn | grep 8000
```

2. Остановите процесс или измените порт в `.env.prod`:
```bash
APP_PORT=8001
PROMETHEUS_PORT=9091
GRAFANA_PORT=3001
```

---

## Проблема: Сервис не запускается

**Решение:**
```bash
# Проверьте логи
docker-compose -f docker/docker-compose.yml logs [service_name]

# Примеры:
docker-compose -f docker/docker-compose.yml logs app
docker-compose -f docker/docker-compose.yml logs postgres
docker-compose -f docker/docker-compose.yml logs prometheus
```

**Частые проблемы:**

### Приложение не может подключиться к БД
```bash
# Проверьте статус PostgreSQL
docker-compose -f docker/docker-compose.yml ps postgres

# Проверьте логи
docker-compose -f docker/docker-compose.yml logs postgres | tail -50
```

### Миграции не применяются
```bash
# Примените миграции вручную
docker-compose -f docker/docker-compose.yml exec app alembic -c app/alembic.ini upgrade head
```

### Ошибка сборки Docker образа
```bash
# Пересоберите без кэша
docker-compose -f docker/docker-compose.yml build --no-cache app
docker-compose -f docker/docker-compose.yml up -d
```

---

## Проблема: Endpoint недоступен

**Проверка:**

1. **Проверьте статус контейнеров:**
```bash
docker-compose -f docker/docker-compose.yml ps
```

Все должны быть `Up (healthy)` или `Up`.

2. **Проверьте логи приложения:**
```bash
docker-compose -f docker/docker-compose.yml logs app | tail -50
```

3. **Проверьте health endpoint:**
```bash
curl http://localhost:8000/health
```

4. **Подождите больше времени** (30-60 секунд) если контейнеры только что запустились.

---

## Проблема: Ошибка при загрузке видео

**Проверка:**

1. **Формат файла:**
   - Поддерживаются: mp4, avi, mov, mkv
   - Убедитесь, что файл не поврежден

2. **Размер файла:**
   - Слишком большие файлы могут вызывать таймауты
   - Попробуйте файл меньше 100MB

3. **Логи:**
```bash
docker-compose -f docker/docker-compose.yml logs app | grep -i error
```

---

## Полная перезагрузка

Если ничего не помогает:

```bash
# 1. Остановить все
docker-compose -f docker/docker-compose.yml down -v

# 2. Удалить образы (опционально)
docker-compose -f docker/docker-compose.yml down --rmi all

# 3. Очистить Docker
docker system prune -f

# 4. Запустить заново
./scripts/start_simple.sh
```

---

## Быстрая проверка работоспособности

```bash
# 1. Проверка Docker
docker ps

# 2. Проверка контейнеров
docker-compose -f docker/docker-compose.yml ps

# 3. Проверка health
curl http://localhost:8000/health

# 4. Проверка метрик
curl http://localhost:8000/metrics | head -20

# 5. Проверка Prometheus
curl http://localhost:9090/-/healthy

# 6. Проверка Grafana
curl http://localhost:3000/api/health
```

Все должны вернуть `200 OK` или успешный ответ.

---

## Использование простого docker-compose.yml

Если `docker-compose.prod.yml` не работает, используйте обычный:

```bash
# Запуск
docker-compose -f docker/docker-compose.yml up -d --build

# Проверка
docker-compose -f docker/docker-compose.yml ps

# Логи
docker-compose -f docker/docker-compose.yml logs -f

# Остановка
docker-compose -f docker/docker-compose.yml down
```

---

## Получение помощи

Если проблема не решена, соберите информацию:

```bash
# Статус контейнеров
docker-compose -f docker/docker-compose.yml ps > status.txt

# Логи всех сервисов
docker-compose -f docker/docker-compose.yml logs > logs.txt

# Версии
docker --version
docker-compose --version
```

---

**Удачи! 🚀**

