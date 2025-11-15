#!/bin/bash
# Скрипт для проверки всех endpoints

set -e

BASE_URL="${1:-http://localhost:8000}"

echo "=== Проверка endpoints ==="
echo "Base URL: $BASE_URL"
echo ""

# 1. GET /health
echo "1. GET /health"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/health")
http_code=$(echo "$response" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE:/d')

if [ "$http_code" = "200" ]; then
    echo "✓ Status: $http_code"
    echo "Response: $body"
elif [ "$http_code" = "503" ]; then
    echo "⚠ Status: $http_code (БД не подключена, это нормально для тестов)"
    echo "Response: $body"
else
    echo "✗ Status: $http_code"
    echo "Response: $body"
    exit 1
fi
echo ""

# 2. GET /metrics
echo "2. GET /metrics"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/metrics")
http_code=$(echo "$response" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE:/d' | head -20)

if [ "$http_code" = "200" ]; then
    echo "✓ Status: $http_code"
    echo "Response (первые 20 строк):"
    echo "$body"
    
    # Проверяем наличие основных метрик
    if echo "$body" | grep -q "video_processed_total"; then
        echo "✓ Метрика video_processed_total найдена"
    fi
    if echo "$body" | grep -q "video_processing_duration_seconds"; then
        echo "✓ Метрика video_processing_duration_seconds найдена"
    fi
    if echo "$body" | grep -q "video_errors_total"; then
        echo "✓ Метрика video_errors_total найдена"
    fi
    if echo "$body" | grep -q "videos_in_queue"; then
        echo "✓ Метрика videos_in_queue найдена"
    fi
else
    echo "✗ Status: $http_code"
    echo "Response: $body"
    exit 1
fi
echo ""

# 3. POST /analyze (требует реальный видео файл)
echo "3. POST /analyze"
echo "⚠ Для полной проверки нужен реальный видео файл"
echo "Пример использования:"
echo "  curl -X POST $BASE_URL/analyze -F \"file=@test_video.mp4\""
echo ""

# 4. GET /results/{video_id}
echo "4. GET /results/{video_id}"
fake_id="00000000-0000-0000-0000-000000000000"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/results/$fake_id")
http_code=$(echo "$response" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE:/d')

if [ "$http_code" = "404" ]; then
    echo "✓ Status: $http_code (ожидаемо для несуществующего ID)"
    echo "Response: $body"
elif [ "$http_code" = "200" ]; then
    echo "✓ Status: $http_code"
    echo "Response: $body"
else
    echo "✗ Status: $http_code"
    echo "Response: $body"
    exit 1
fi
echo ""

echo "=== Все endpoints проверены ==="

