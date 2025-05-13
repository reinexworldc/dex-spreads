#!/bin/bash

# Переходим в директорию бэкенда
cd backend

# Устанавливаем зависимости, если они еще не установлены
if [ ! -d "venv" ]; then
  echo "Создаем виртуальное окружение и устанавливаем зависимости..."
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  echo "Активируем виртуальное окружение..."
  source venv/bin/activate
fi

# Запускаем Flask-приложение
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

echo "Запускаем Flask-сервер на http://localhost:5000"
flask run --host=0.0.0.0 --port=5000 