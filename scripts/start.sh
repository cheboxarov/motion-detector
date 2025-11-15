#!/bin/bash

set -e

echo "🚀 Запуск Video Analysis Service"
echo "=================================="

# Проверка Docker
echo ""
echo "📦 Проверка Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker не запущен!"
    echo ""
    echo "Для macOS:"
    echo "  1. Откройте Docker Desktop"
    echo "  2. Дождитесь полной загрузки (зеленый индикатор)"
    echo "  3. Запустите этот скрипт снова"
    echo ""
    exit 1
fi
echo "✅ Docker запущен"

# Проверка .env.prod
echo ""
echo "📝 Проверка переменных окружения..."
if [ ! -f ../.env.prod ]; then
    echo "⚠️  Файл .env.prod не найден, создаю..."
    cat > ../.env.prod << EOF
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
    echo "✅ Файл .env.prod создан"
else
    echo "✅ Файл .env.prod найден"
fi

# Переход в корневую директорию проекта
cd "$(dirname "$0")/.."

# Остановка существующих контейнеров
echo ""
echo "🛑 Остановка существующих контейнеров..."
docker-compose -f docker/docker-compose.prod.yml down 2>/dev/null || true

# Запуск
echo ""
echo "🏗️  Запуск сервисов..."
docker-compose -f docker/docker-compose.prod.yml --env-file .env.prod up -d --build

# Ожидание готовности
echo ""
echo "⏳ Ожидание готовности сервисов..."
sleep 10

# Проверка статуса
echo ""
echo "📊 Статус сервисов:"
docker-compose -f docker/docker-compose.prod.yml ps

# Проверка health endpoint
echo ""
echo "🔍 Проверка health endpoint..."
sleep 5
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API доступен!"
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
        break
    else
        echo "⏳ Ожидание... ($i/10)"
        sleep 2
    fi
done

echo ""
echo "=================================="
echo "✅ Готово!"
echo ""
echo "🌐 Доступные сервисы:"
echo "  - API:              http://localhost:8000"
echo "  - API Docs:         http://localhost:8000/docs"
echo "  - Prometheus:       http://localhost:9090"
echo "  - Grafana:          http://localhost:3000 (admin/admin)"
echo ""
echo "📝 Для просмотра логов:"
echo "  docker-compose -f docker/docker-compose.prod.yml logs -f"
echo ""
echo "🛑 Для остановки:"
echo "  docker-compose -f docker/docker-compose.prod.yml down"
echo ""

