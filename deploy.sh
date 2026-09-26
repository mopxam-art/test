#!/bin/bash
set -e

echo "=== Запуск OpenClaw в Docker ==="
cd "$(dirname "$0")"

# Создаем папки при необходимости
mkdir -p data/config

# Если нет локального .env, создаем из шаблона
if [ ! -f .env ] && [ -f .env.example ]; then
  echo "Создаю .env из .env.example..."
  cp .env.example .env
fi

# Если нет рабочего openclaw.json, инициализируем из стартового шаблона
if [ ! -f data/config/openclaw.json ] && [ -f data/config/openclaw.json.starter ]; then
  echo "Инициализирую data/config/openclaw.json из стартового шаблона..."
  cp data/config/openclaw.json.starter data/config/openclaw.json
fi

chown -R 1000:1000 data 2>/dev/null || true
chmod -R 775 data 2>/dev/null || true

# Запуск контейнера в фоне
docker compose up -d

echo ""
echo "=== Сервис OpenClaw запущен! ==="
echo "Панель управления доступна:"
echo "- Localhost: http://127.0.0.1:18789"
echo "- Сеть / Tailscale: http://100.86.75.16:18789 (токен по умолчанию: openclaw123)"
echo ""
echo "Для просмотра логов: docker compose logs -f openclaw"
