#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Проверка Docker конфигурации для проекта dex-spreads"
echo "-------------------------------------------------"

# Проверка наличия Docker
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker установлен"
    docker --version
else
    echo -e "${RED}✗${NC} Docker не установлен. Установите Docker перед запуском проекта."
    exit 1
fi

# Проверка наличия Docker Compose
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose установлен"
    docker-compose --version
else
    echo -e "${RED}✗${NC} Docker Compose не установлен. Установите Docker Compose перед запуском проекта."
    exit 1
fi

echo
echo "Проверка наличия необходимых файлов:"

# Проверка наличия Dockerfile для фронтенда
if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}✓${NC} Dockerfile для фронтенда найден"
else
    echo -e "${RED}✗${NC} Dockerfile для фронтенда не найден"
fi

# Проверка наличия Dockerfile для бэкенда
if [ -f "backend/Dockerfile" ]; then
    echo -e "${GREEN}✓${NC} Dockerfile для бэкенда найден"
else
    echo -e "${RED}✗${NC} Dockerfile для бэкенда не найден"
fi

# Проверка наличия Dockerfile.main для скрипта main.py
if [ -f "backend/Dockerfile.main" ]; then
    echo -e "${GREEN}✓${NC} Dockerfile.main для скрипта найден"
else
    echo -e "${RED}✗${NC} Dockerfile.main для скрипта не найден"
fi

# Проверка наличия docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓${NC} docker-compose.yml найден"
else
    echo -e "${RED}✗${NC} docker-compose.yml не найден"
fi

# Проверка наличия базы данных
if [ -f "backend/db.sqlite3" ]; then
    echo -e "${GREEN}✓${NC} База данных SQLite найдена"
else
    echo -e "${YELLOW}⚠${NC} База данных SQLite не найдена. Будет создана при первом запуске."
fi

echo
echo "Проверка доступности портов:"

# Проверка занятости порта 3000
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}✗${NC} Порт 3000 занят другим процессом. Освободите его перед запуском."
else
    echo -e "${GREEN}✓${NC} Порт 3000 свободен для фронтенда"
fi

# Проверка занятости порта 5000
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}✗${NC} Порт 5000 занят другим процессом. Освободите его перед запуском."
else
    echo -e "${GREEN}✓${NC} Порт 5000 свободен для бэкенда"
fi

echo
echo "Все проверки завершены."
echo "Для запуска проекта выполните: docker-compose up -d"
echo "Для просмотра логов: docker-compose logs -f" 