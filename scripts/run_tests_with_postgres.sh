#!/bin/bash
# Скрипт для запуска тестов с реальной PostgreSQL из docker-compose

set -e

# Переход в корневую директорию проекта
cd "$(dirname "$0")/.."

echo "Запуск PostgreSQL через docker-compose..."
docker-compose -f docker/docker-compose.yml up -d postgres

echo "Ожидание готовности PostgreSQL..."
sleep 5

# Проверяем подключение
until docker-compose -f docker/docker-compose.yml exec -T postgres psql -U video_user -d video_db -c "SELECT 1;" > /dev/null 2>&1; do
    echo "Ожидание PostgreSQL..."
    sleep 2
done

echo "Применение миграций..."
export DATABASE_URL="postgresql://video_user:video_password@localhost:5433/video_db"
source venv/bin/activate
alembic -c app/alembic.ini upgrade head

echo "Запуск тестов..."
pytest tests/ -v --tb=short

echo "Тесты завершены. PostgreSQL продолжает работать."
echo "Для остановки: docker-compose -f docker/docker-compose.yml stop postgres"

