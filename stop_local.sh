#!/bin/bash

echo "Останавливаем компоненты проекта Dex Spreads..."

# Останавливаем процессы по сохраненным PID
if [ -f .update_db.pid ]; then
    PID=$(cat .update_db.pid)
    if ps -p $PID > /dev/null; then
        echo "Останавливаем процесс обновления БД (PID: $PID)..."
        kill $PID
    fi
    rm .update_db.pid
fi

if [ -f .flask.pid ]; then
    PID=$(cat .flask.pid)
    if ps -p $PID > /dev/null; then
        echo "Останавливаем Flask-сервер (PID: $PID)..."
        kill $PID
    fi
    rm .flask.pid
fi

if [ -f .frontend.pid ]; then
    PID=$(cat .frontend.pid)
    if ps -p $PID > /dev/null; then
        echo "Останавливаем фронтенд (PID: $PID)..."
        kill $PID
    fi
    rm .frontend.pid
fi

echo "Все процессы остановлены!"
