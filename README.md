# OpenClaw Starter Kit (Docker)

Чистая базовая конфигурация OpenClaw Gateway в Docker с поддержкой отката к заводским настройкам.

---

## 🚀 Быстрый запуск

1. **Создайте файл окружения `.env`**:
   Скопируйте пример:
   ```bash
   cp .env.example .env
   ```
   Укажите ваш API ключ OpenRouter и токен доступа в `.env`:
   ```ini
   OPENROUTER_API_KEY=sk-or-v1-...
   OPENCLAW_GATEWAY_TOKEN=openclaw123
   ```

2. **Запустите развертывание**:
   ```bash
   ./deploy.sh
   # или напрямую через docker compose:
   docker compose up -d
   ```

3. **Откройте панель управления**:
   - Локально: [http://localhost:18789](http://localhost:18789)
   - Через сеть / Tailscale: `http://<IP_СЕРВЕРА>:18789`
   - Токен по умолчанию: `openclaw123` (или указанный в конфиге)

---

## 📦 Образы Docker

В локальном Docker реестре сохранены базовые теги чистого заводского образа:
- `openclaw:starter` — неизменяемый стартовый слепок
- `openclaw:clean` — чистый образ OpenClaw
- `openclaw-clean:latest` — актуальный заводской образ
- `ghcr.io/openclaw/openclaw:latest` — официальный upstream образ

---

## 🔄 Как откатиться к заводским настройкам (Rollback)

Если в процессе экспериментов что-то сломалось или поведение загрязнилось:

### 1. Откат конфигурации к стартовой
```bash
# Остановите шлюз
docker compose down

# Скопируйте чистый шаблон конфигурации
cp data/config/openclaw.json.starter data/config/openclaw.json

# Запустите заново
docker compose up -d
```

### 2. Запуск со стартового образа Docker
В `.env` укажите:
```ini
OPENCLAW_IMAGE=openclaw:starter
```
и выполните:
```bash
docker compose up -d --force-recreate
```

### 3. Полный откат через Git
```bash
git checkout v1.0.0-starter -- docker-compose.yml data/config/openclaw.json.starter deploy.sh
```

---

## 📂 Структура проекта

```text
├── docker-compose.yml              # Описание сервиса OpenClaw
├── deploy.sh                       # Скрипт развертывания
├── .env.example                    # Пример переменных окружения
├── .gitignore                      # Защита от утечки секретов и баз данных
├── data/
│   └── config/
│       ├── openclaw.json.starter   # Чистый стартовый шаблон настроек
│       └── openclaw.json           # Рабочий конфиг (не коммитится в Git)
└── README.md                       # Данная инструкция
```

> **Безопасность:** Рабочие токены, персональные ключи OpenRouter/GitHub и база данных SQLite исключены из Git через `.gitignore`.
