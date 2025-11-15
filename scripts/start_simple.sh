#!/bin/bash

set -e

echo "🚀 Простой запуск (docker-compose.yml)"
echo "======================================="

# Проверка Docker
echo ""
echo "📦 Проверка Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker не запущен!"
    echo ""
    echo "Для macOS:"
    echo "  1. Откройте Docker Desktop"
    echo "  2. Дождитесь полной загрузки"
    echo "  3. Запустите этот скрипт снова"
    echo ""
    exit 1
fi
echo "✅ Docker запущен"

# Переход в корневую директорию проекта
cd "$(dirname "$0")/.."

# Остановка существующих контейнеров
echo ""
echo "🛑 Остановка существующих контейнеров..."
docker-compose -f docker/docker-compose.yml down 2>/dev/null || true

# Запуск
echo ""
echo "🏗️  Запуск сервисов..."
docker-compose -f docker/docker-compose.yml up -d --build

# Ожидание готовности
echo ""
echo "⏳ Ожидание готовности сервисов..."
sleep 15

# Проверка статуса
echo ""
echo "📊 Статус сервисов:"
docker-compose -f docker/docker-compose.yml ps

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
echo "======================================="
echo "✅ Готово!"
echo ""
echo "🌐 Доступные сервисы:"
echo "  - API:              http://localhost:8000"
echo "  - API Docs:         http://localhost:8000/docs"
echo "  - Prometheus:       http://localhost:9090"
echo "  - Grafana:          http://localhost:3000 (admin/admin)"
echo ""
echo "📝 Для просмотра логов:"
echo "  docker-compose -f docker/docker-compose.yml logs -f"
echo ""
echo "🛑 Для остановки:"
echo "  docker-compose -f docker/docker-compose.yml down"
echo ""

